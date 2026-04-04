package com.bounswe.group9.mobile.ui.eventdetail

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.Accessible
import androidx.compose.material.icons.filled.Group
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.BookmarkBorder
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.bounswe.group9.mobile.data.remote.EventDetailDto
import com.bounswe.group9.mobile.data.remote.EventLimitedDto
import com.bounswe.group9.mobile.data.remote.EquipmentDto
import com.bounswe.group9.mobile.data.remote.VenueMetadataDto
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EventDetailScreen(
    viewModel: EventDetailViewModel,
    eventId: String,
    token: String?,
    currentUserId: String? = null,
    onBack: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(eventId, token) {
        viewModel.loadEvent(eventId, token)
    }

    // Show action error as snackbar
    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(uiState.actionError) {
        uiState.actionError?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearActionError()
        }
    }

    val isActiveEvent = uiState.fullDetail?.status == "published"
    val isHost = currentUserId != null && uiState.fullDetail?.host_id == currentUserId

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Event Details", maxLines = 1, overflow = TextOverflow.Ellipsis) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
        bottomBar = {
            // Show action buttons only for authenticated non-host users viewing active events
            if (token != null && uiState.fullDetail != null && isActiveEvent && !isHost) {
                ActionBottomBar(
                    event = uiState.fullDetail!!,
                    onToggleBookmark = { viewModel.toggleBookmark() },
                    onGoing = { viewModel.setGoing() },
                    onRemoveAttendance = { viewModel.removeAttendance() }
                )
            }
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            when {
                uiState.isLoading -> LoadingState()
                uiState.errorMessage != null -> ErrorState(
                    message = uiState.errorMessage!!,
                    onRetry = { viewModel.loadEvent(eventId, token) }
                )
                uiState.fullDetail != null -> FullDetailContent(uiState.fullDetail!!)
                uiState.limitedPreview != null -> LimitedPreviewContent(uiState.limitedPreview!!)
            }
        }
    }
}

// region Loading & Error States

@Composable
private fun LoadingState() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        CircularProgressIndicator()
    }
}

@Composable
private fun ErrorState(message: String, onRetry: () -> Unit) {
    Column(
        Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(Icons.Default.Info, contentDescription = null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.error)
        Spacer(Modifier.height(16.dp))
        Text("Something went wrong", style = MaterialTheme.typography.titleMedium)
        Spacer(Modifier.height(8.dp))
        Text(message, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(24.dp))
        Button(onClick = onRetry) { Text("Retry") }
    }
}

// endregion

// region Limited Preview

@Composable
private fun LimitedPreviewContent(event: EventLimitedDto) {
    Column(
        Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(Icons.Default.Lock, contentDescription = null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(16.dp))
        Text(event.title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        Text(formatDateRange(event.start_datetime, event.end_datetime), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(12.dp))
        if (event.categories.isNotEmpty()) {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                event.categories.take(3).forEach { cat ->
                    SuggestionChip(onClick = {}, label = { Text(cat.name, fontSize = 12.sp) })
                }
            }
        }
        Spacer(Modifier.height(16.dp))
        val reason = when {
            event.visibility == "private" -> "This is a private event. Request access from the host to see full details."
            event.status == "cancelled" -> "This event has been cancelled."
            else -> "Sign in to view full event details."
        }
        Text(reason, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

// endregion

// region Full Detail

@Composable
private fun FullDetailContent(event: EventDetailDto) {
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
    ) {
        // Image gallery
        if (event.images.isNotEmpty()) {
            ImageGallery(event.images.map { it.image_url })
        }

        Column(Modifier.padding(16.dp)) {
            // Badges row
            BadgeRow(event)

            Spacer(Modifier.height(8.dp))

            // Title
            Text(event.title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)

            Spacer(Modifier.height(4.dp))

            // Status chip
            if (event.status == "cancelled") {
                SuggestionChip(onClick = {}, label = { Text("Cancelled") }, colors = SuggestionChipDefaults.suggestionChipColors(containerColor = MaterialTheme.colorScheme.errorContainer))
                Spacer(Modifier.height(8.dp))
            }
            if (event.status == "ended") {
                SuggestionChip(onClick = {}, label = { Text("This event has ended") }, colors = SuggestionChipDefaults.suggestionChipColors(containerColor = MaterialTheme.colorScheme.surfaceVariant))
                Spacer(Modifier.height(8.dp))
            }

            // Date & Time
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.AccessTime, contentDescription = null, modifier = Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.width(6.dp))
                Text(formatDateRange(event.start_datetime, event.end_datetime), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }

            Spacer(Modifier.height(12.dp))

            // Locations
            event.locations.sortedBy { it.order_index }.forEach { loc ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.LocationOn, contentDescription = null, modifier = Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.width(6.dp))
                    Text(
                        loc.name + if (loc.is_primary) " (Primary)" else "",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Spacer(Modifier.height(4.dp))
            }

            Spacer(Modifier.height(12.dp))

            // Attendees
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Group, contentDescription = null, modifier = Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.width(6.dp))
                val isPast = event.status == "ended" || event.status == "cancelled"
                val attendeeText = buildString {
                    append("${event.going_count} ${if (isPast) "went" else "going"}")
                    if (event.attendee_limit != null) append(" / ${event.attendee_limit} max")
                }
                Text(attendeeText, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (event.is_full == true) {
                    Spacer(Modifier.width(8.dp))
                    Text("Full", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.error, modifier = Modifier.background(MaterialTheme.colorScheme.errorContainer, RoundedCornerShape(4.dp)).padding(horizontal = 6.dp, vertical = 2.dp))
                }
            }

            Spacer(Modifier.height(16.dp))

            // Categories
            if (event.categories.isNotEmpty()) {
                Row(
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    event.categories.forEach { cat ->
                        SuggestionChip(onClick = {}, label = { Text(cat.name, fontSize = 12.sp) })
                    }
                }
                Spacer(Modifier.height(16.dp))
            }

            // Description
            SectionHeader("About")
            Text(event.description, style = MaterialTheme.typography.bodyMedium)

            // Venue Metadata
            if (event.venue_metadata != null) {
                Spacer(Modifier.height(16.dp))
                VenueMetadataSection(event.venue_metadata)
            }

            // Equipment
            if (event.equipment_requirements.isNotEmpty()) {
                Spacer(Modifier.height(16.dp))
                EquipmentSection(event.equipment_requirements)
            }

            // Accessibility features
            if (event.venue_metadata != null) {
                val a = event.venue_metadata
                val features = buildList {
                    if (a.wheelchair_access) add("Wheelchair accessible")
                    if (a.accessible_restroom) add("Accessible restroom")
                    if (a.elevator_available) add("Elevator available")
                    if (a.seating_available) add("Seating available")
                    if (a.captions_support) add("Captions/sign language")
                    if (a.quiet_friendly) add("Quiet-friendly")
                }
                if (features.isNotEmpty()) {
                    Spacer(Modifier.height(16.dp))
                    SectionHeader("Accessibility")
                    Row(
                        modifier = Modifier.horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        features.forEach { f ->
                            SuggestionChip(
                                onClick = {},
                                icon = { Icon(Icons.Default.Accessible, contentDescription = null, modifier = Modifier.size(16.dp)) },
                                label = { Text(f, fontSize = 12.sp) }
                            )
                        }
                    }
                }
            }

            Spacer(Modifier.height(32.dp))
        }
    }
}

// endregion

// region Sub-components

@Composable
private fun ImageGallery(imageUrls: List<String>) {
    if (imageUrls.size == 1) {
        AsyncImage(
            model = imageUrls[0],
            contentDescription = "Event image",
            modifier = Modifier.fillMaxWidth().height(220.dp),
            contentScale = ContentScale.Crop
        )
    } else {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState())
                .height(220.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            imageUrls.forEach { url ->
                AsyncImage(
                    model = url,
                    contentDescription = "Event image",
                    modifier = Modifier
                        .width(300.dp)
                        .fillMaxHeight()
                        .clip(RoundedCornerShape(4.dp)),
                    contentScale = ContentScale.Crop
                )
            }
        }
    }
}

@Composable
private fun BadgeRow(event: EventDetailDto) {
    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        if (event.visibility == "private") {
            Badge(containerColor = Color(0xFF333333)) {
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)) {
                    Icon(Icons.Default.Lock, contentDescription = null, modifier = Modifier.size(10.dp), tint = Color.White)
                    Spacer(Modifier.width(2.dp))
                    Text("Private", fontSize = 10.sp, color = Color.White)
                }
            }
        }
        if (event.is_age_restricted) {
            Badge(containerColor = Color(0xFF333333)) {
                Text("18+", fontSize = 10.sp, color = Color.White, modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp))
            }
        }
        if (event.is_full == true) {
            Badge(containerColor = MaterialTheme.colorScheme.error) {
                Text("Full", fontSize = 10.sp, color = Color.White, modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp))
            }
        }
    }
}

@Composable
private fun SectionHeader(title: String) {
    Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
    Spacer(Modifier.height(6.dp))
}

@Composable
private fun VenueMetadataSection(venue: VenueMetadataDto) {
    SectionHeader("Venue Info")
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        venue.price?.let { InfoRow("Price", it) }
        venue.language?.let { InfoRow("Language", it) }
        venue.health_requirements?.let { InfoRow("Health Requirements", it) }
    }
}

@Composable
private fun EquipmentSection(equipment: List<EquipmentDto>) {
    SectionHeader("Equipment")
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        equipment.forEach { eq ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    if (eq.is_required) "• ${eq.item_name} (Required)" else "• ${eq.item_name} (Optional)",
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row {
        Text("$label: ", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
        Text(value, style = MaterialTheme.typography.bodyMedium)
    }
}

// endregion

// region Helpers

private fun formatDateRange(start: String, end: String): String {
    return try {
        // Backend returns ISO 8601 with timezone (e.g. 2026-04-15T14:30:00+00:00)
        // Use ISO parser that handles the offset, then display in device local timezone
        val parser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
        val display = SimpleDateFormat("EEE, MMM d · HH:mm", Locale.getDefault())
        val displayEnd = SimpleDateFormat("HH:mm", Locale.getDefault())
        val startDate = parser.parse(start)
        val endDate = parser.parse(end)
        if (startDate != null && endDate != null) {
            "${display.format(startDate)} – ${displayEnd.format(endDate)}"
        } else {
            start
        }
    } catch (_: Exception) {
        start
    }
}

// endregion

// region Action Bottom Bar

@Composable
private fun ActionBottomBar(
    event: EventDetailDto,
    onToggleBookmark: () -> Unit,
    onGoing: () -> Unit,
    onRemoveAttendance: () -> Unit
) {
    val isBookmarked = event.is_bookmarked == true
    val attendanceStatus = event.attendance_status
    val isFull = event.is_full == true

    Surface(
        tonalElevation = 3.dp,
        shadowElevation = 8.dp
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Bookmark button
            OutlinedButton(
                onClick = onToggleBookmark,
                colors = if (isBookmarked) ButtonDefaults.outlinedButtonColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                ) else ButtonDefaults.outlinedButtonColors()
            ) {
                Icon(
                    if (isBookmarked) Icons.Default.Bookmark else Icons.Default.BookmarkBorder,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(Modifier.width(4.dp))
                Text(if (isBookmarked) "Saved" else "Bookmark", fontSize = 13.sp)
            }

            // Going button
            if (attendanceStatus == "going") {
                Button(
                    onClick = onRemoveAttendance,
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("Going", fontSize = 13.sp)
                }
            } else {
                Button(
                    onClick = onGoing,
                    enabled = !isFull,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary,
                        disabledContainerColor = MaterialTheme.colorScheme.surfaceVariant
                    )
                ) {
                    Text(if (isFull) "Full" else "Going", fontSize = 13.sp)
                }
            }
        }
    }
}

// endregion
