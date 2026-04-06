package com.bounswe.group9.mobile.ui.discovery

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import coil.compose.AsyncImage
import com.bounswe.group9.mobile.data.remote.EventListItemDto
import com.bounswe.group9.mobile.ui.common.formatEventDate
import org.maplibre.android.MapLibre
import org.maplibre.android.annotations.IconFactory
import org.maplibre.android.annotations.MarkerOptions
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.maps.MapView

private const val MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty"
// Default center: Istanbul
private val DEFAULT_LAT = 41.0082
private val DEFAULT_LNG = 28.9784
private val DEFAULT_ZOOM = 10.0

@Composable
fun EventMapView(
    events: List<EventListItemDto>,
    onEventClick: (String) -> Unit
) {
    var selectedEvent by remember { mutableStateOf<EventListItemDto?>(null) }
    val markerToEvent = remember { mutableMapOf<Long, EventListItemDto>() }

    Box(modifier = Modifier.fillMaxSize()) {
        AndroidView(
            factory = { context ->
                MapLibre.getInstance(context)
                MapView(context).apply {
                    getMapAsync { map ->
                        map.setStyle(MAP_STYLE) { _ ->
                            map.cameraPosition = CameraPosition.Builder()
                                .target(LatLng(DEFAULT_LAT, DEFAULT_LNG))
                                .zoom(DEFAULT_ZOOM)
                                .build()

                            val icon = IconFactory.getInstance(context)
                                .fromBitmap(createMarkerBitmap())

                            events.filter { it.primary_location != null }.forEach { event ->
                                val loc = event.primary_location!!
                                val marker = map.addMarker(
                                    MarkerOptions()
                                        .position(LatLng(loc.latitude, loc.longitude))
                                        .icon(icon)
                                )
                                marker?.let { markerToEvent[it.id] = event }
                            }

                            map.setOnMarkerClickListener { marker ->
                                selectedEvent = markerToEvent[marker.id]
                                true
                            }

                            map.addOnMapClickListener {
                                selectedEvent = null
                                true
                            }
                        }
                    }
                    onCreate(null)
                }
            },
            modifier = Modifier.fillMaxSize()
        )

        // Popup card when marker tapped
        selectedEvent?.let { event ->
            EventMapPopup(
                event = event,
                onDismiss = { selectedEvent = null },
                onViewDetail = { onEventClick(event.id) },
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(16.dp)
            )
        }
    }
}

@Composable
private fun EventMapPopup(
    event: EventListItemDto,
    onDismiss: () -> Unit,
    onViewDetail: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(8.dp)
    ) {
        Row(modifier = Modifier.padding(12.dp)) {
            // Image
            Box(
                modifier = Modifier
                    .size(72.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(MaterialTheme.colorScheme.tertiary.copy(alpha = 0.25f))
            ) {
                if (event.primary_image_url != null) {
                    AsyncImage(
                        model = event.primary_image_url,
                        contentDescription = event.title,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize()
                    )
                }
            }

            Spacer(Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    event.title,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.onSurface,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    formatEventDate(event.start_datetime),
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.tertiary,
                    fontWeight = FontWeight.SemiBold
                )
                if (event.categories.isNotEmpty()) {
                    Spacer(Modifier.height(4.dp))
                    Text(
                        event.categories.first().name,
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Spacer(Modifier.height(8.dp))
                TextButton(
                    onClick = onViewDetail,
                    contentPadding = PaddingValues(0.dp),
                    modifier = Modifier.height(24.dp)
                ) {
                    Text(
                        "View Details →",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.tertiary
                    )
                }
            }

            IconButton(onClick = onDismiss, modifier = Modifier.size(28.dp)) {
                Text("✕", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

// ── Location picker map (used in Create Event Step 2) ──────────────────────────

@Composable
fun LocationPickerMapView(
    selectedLat: Double?,
    selectedLng: Double?,
    onLocationPicked: (lat: Double, lng: Double) -> Unit,
    modifier: Modifier = Modifier
) {
    val markerRef = remember { mutableStateOf<org.maplibre.android.annotations.Marker?>(null) }

    Box(modifier = modifier) {
        AndroidView(
            factory = { context ->
                MapLibre.getInstance(context)
                MapView(context).apply {
                    getMapAsync { map ->
                        map.setStyle(MAP_STYLE) { _ ->
                            // Center on existing pin or Istanbul default
                            val initLat = selectedLat ?: DEFAULT_LAT
                            val initLng = selectedLng ?: DEFAULT_LNG
                            val zoom = if (selectedLat != null) 14.0 else DEFAULT_ZOOM
                            map.cameraPosition = CameraPosition.Builder()
                                .target(LatLng(initLat, initLng))
                                .zoom(zoom)
                                .build()

                            val icon = IconFactory.getInstance(context)
                                .fromBitmap(createMarkerBitmap())

                            // Place initial marker if coords exist
                            if (selectedLat != null && selectedLng != null) {
                                markerRef.value = map.addMarker(
                                    MarkerOptions()
                                        .position(LatLng(selectedLat, selectedLng))
                                        .icon(icon)
                                )
                            }

                            map.addOnMapClickListener { latLng ->
                                // Remove old marker
                                markerRef.value?.let { map.removeMarker(it) }
                                // Add new marker
                                markerRef.value = map.addMarker(
                                    MarkerOptions()
                                        .position(latLng)
                                        .icon(icon)
                                )
                                onLocationPicked(latLng.latitude, latLng.longitude)
                                true
                            }
                        }
                    }
                    onCreate(null)
                }
            },
            modifier = Modifier.fillMaxSize()
        )

        // Hint overlay at the top
        Surface(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(top = 10.dp),
            shape = RoundedCornerShape(20.dp),
            color = Color.Black.copy(alpha = 0.6f)
        ) {
            Text(
                text = "📍 Tap map to pin location",
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 6.dp),
                color = Color.White,
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium
            )
        }

        // Coordinate display at the bottom if selected
        if (selectedLat != null && selectedLng != null) {
            Surface(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 10.dp),
                shape = RoundedCornerShape(20.dp),
                color = Color(0xFF493628).copy(alpha = 0.9f)
            ) {
                Text(
                    text = "%.5f, %.5f".format(selectedLat, selectedLng),
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 6.dp),
                    color = Color.White,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
    }
}

private fun createMarkerBitmap(): Bitmap {
    val size = 80
    val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    val paint = Paint(Paint.ANTI_ALIAS_FLAG)

    // Circle
    paint.color = android.graphics.Color.parseColor("#493628") // BrandDark
    canvas.drawCircle(size / 2f, size / 2f - 8f, 28f, paint)

    // Pin tail
    val path = android.graphics.Path()
    path.moveTo(size / 2f - 10f, size / 2f + 18f)
    path.lineTo(size / 2f + 10f, size / 2f + 18f)
    path.lineTo(size / 2f, size / 2f + 38f)
    path.close()
    canvas.drawPath(path, paint)

    // White dot center
    paint.color = android.graphics.Color.WHITE
    canvas.drawCircle(size / 2f, size / 2f - 8f, 10f, paint)

    return bitmap
}
