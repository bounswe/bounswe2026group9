package com.bounswe.group9.mobile.ui.discovery

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Search
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
import coil.compose.AsyncImage
import com.bounswe.group9.mobile.data.remote.CategoryDto
import com.bounswe.group9.mobile.data.remote.EventListItemDto
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DiscoveryScreen(
    viewModel: DiscoveryViewModel,
    token: String?,
    onEventClick: (String) -> Unit,
    onLoginClick: () -> Unit = {},
    onLogout: () -> Unit = {},
    username: String? = null
) {
    val uiState by viewModel.uiState.collectAsState()
    val listState = rememberLazyListState()
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val scope = rememberCoroutineScope()
    var showFilterSheet by remember { mutableStateOf(false) }
    var isMapView by remember { mutableStateOf(true) } // default: map

    LaunchedEffect(token) { viewModel.setToken(token) }

    // Infinite scroll
    LaunchedEffect(listState.firstVisibleItemIndex, uiState.events.size) {
        val lastVisible = listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0
        if (lastVisible >= uiState.events.size - 4 && !uiState.isLoadingMore) {
            viewModel.loadNextPage()
        }
    }

    Scaffold(
        floatingActionButton = {
            if (token != null) {
                ExtendedFloatingActionButton(
                    onClick = { /* Create event — Task #? */ },
                    containerColor = MaterialTheme.colorScheme.tertiary,
                    contentColor = Color.White
                ) {
                    Text("+ Create Event", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                }
            }
        },
        topBar = {
            DiscoveryTopBar(
                search = uiState.search,
                onSearchChange = viewModel::onSearchChange,
                activeFilterCount = viewModel.activeFilterCount(),
                onFilterClick = { showFilterSheet = true },
                username = username,
                isLoggedIn = token != null,
                onLoginClick = onLoginClick,
                onLogout = onLogout,
                isMapView = isMapView,
                onViewToggle = { isMapView = !isMapView }
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            when {
                uiState.isLoading -> {
                    CircularProgressIndicator(
                        modifier = Modifier.align(Alignment.Center),
                        color = MaterialTheme.colorScheme.tertiary
                    )
                }
                uiState.errorMessage != null -> {
                    val errorMsg = uiState.errorMessage
                    Column(
                        modifier = Modifier.align(Alignment.Center).padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text("Something went wrong", fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Spacer(Modifier.height(4.dp))
                        Text(errorMsg ?: "", color = MaterialTheme.colorScheme.error, fontSize = 12.sp)
                        Spacer(Modifier.height(8.dp))
                        TextButton(onClick = viewModel::refresh) {
                            Text("Retry", color = MaterialTheme.colorScheme.tertiary)
                        }
                    }
                }
                uiState.displayedEvents.isEmpty() -> {
                    Text(
                        if (uiState.bookmarkedOnly) "No bookmarked events"
                        else if (uiState.goingOnly) "No events you're going to"
                        else "No events found",
                        modifier = Modifier.align(Alignment.Center),
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                else -> {
                    if (isMapView) {
                        EventMapView(
                            events = uiState.displayedEvents,
                            onEventClick = onEventClick
                        )
                    } else {
                        LazyColumn(
                            state = listState,
                            contentPadding = PaddingValues(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            items(uiState.displayedEvents, key = { it.id }) { event ->
                                EventCard(event = event, onClick = { onEventClick(event.id) })
                            }
                            if (uiState.isLoadingMore) {
                                item {
                                    Box(Modifier.fillMaxWidth().padding(16.dp), Alignment.Center) {
                                        CircularProgressIndicator(
                                            modifier = Modifier.size(24.dp),
                                            color = MaterialTheme.colorScheme.tertiary
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Filter bottom sheet
    if (showFilterSheet) {
        ModalBottomSheet(
            onDismissRequest = { showFilterSheet = false },
            sheetState = sheetState,
            containerColor = MaterialTheme.colorScheme.surface
        ) {
            FilterSheetContent(
                uiState = uiState,
                isLoggedIn = token != null,
                onTemporalSelect = viewModel::onTemporalSelected,
                onCategorySelect = viewModel::onCategorySelected,
                onBookmarkedToggle = viewModel::onBookmarkedOnlyToggle,
                onGoingToggle = viewModel::onGoingOnlyToggle,
                onClear = {
                    viewModel.clearFilters()
                    scope.launch { sheetState.hide() }.invokeOnCompletion { showFilterSheet = false }
                },
                onApply = {
                    viewModel.applyFilters()
                    scope.launch { sheetState.hide() }.invokeOnCompletion { showFilterSheet = false }
                }
            )
        }
    }
}

@Composable
private fun DiscoveryTopBar(
    search: String,
    onSearchChange: (String) -> Unit,
    activeFilterCount: Int,
    onFilterClick: () -> Unit,
    username: String?,
    isLoggedIn: Boolean,
    onLoginClick: () -> Unit,
    onLogout: () -> Unit,
    isMapView: Boolean,
    onViewToggle: () -> Unit
) {
    Surface(
        color = MaterialTheme.colorScheme.primary,
        shadowElevation = 4.dp
    ) {
        Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp)) {
            // Brand row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "SOCIAL EVENT MAPPER",
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 2.sp,
                        color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.6f)
                    )
                    Text(
                        text = "Discover",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Light,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                }

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    if (isLoggedIn && username != null) {
                        Box(
                            modifier = Modifier
                                .size(34.dp)
                                .clip(RoundedCornerShape(50))
                                .background(MaterialTheme.colorScheme.tertiary),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = username.take(1).uppercase(),
                                color = Color.White,
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp
                            )
                        }
                        TextButton(
                            onClick = onLogout,
                            colors = ButtonDefaults.textButtonColors(
                                contentColor = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.7f)
                            )
                        ) {
                            Text("Logout", fontSize = 12.sp)
                        }
                    } else {
                        OutlinedButton(
                            onClick = onLoginClick,
                            colors = ButtonDefaults.outlinedButtonColors(
                                contentColor = MaterialTheme.colorScheme.onPrimary
                            ),
                            border = androidx.compose.foundation.BorderStroke(
                                1.dp, MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.4f)
                            ),
                            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                            modifier = Modifier.height(32.dp)
                        ) {
                            Text("Sign In", fontSize = 12.sp)
                        }
                    }
                }
            }

            Spacer(Modifier.height(10.dp))

            // Search + filter row
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedTextField(
                    value = search,
                    onValueChange = onSearchChange,
                    placeholder = { Text("Search events...", fontSize = 13.sp, color = Color.White.copy(alpha = 0.5f)) },
                    leadingIcon = {
                        Icon(Icons.Default.Search, null,
                            tint = Color.White.copy(alpha = 0.6f),
                            modifier = Modifier.size(18.dp))
                    },
                    modifier = Modifier.weight(1f).height(50.dp),
                    shape = RoundedCornerShape(14.dp),
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = MaterialTheme.colorScheme.tertiary,
                        unfocusedBorderColor = Color.White.copy(alpha = 0.25f),
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        cursorColor = MaterialTheme.colorScheme.tertiary
                    )
                )

                // Map/List toggle
                FilledIconButton(
                    onClick = onViewToggle,
                    modifier = Modifier.size(50.dp),
                    shape = RoundedCornerShape(14.dp),
                    colors = IconButtonDefaults.filledIconButtonColors(
                        containerColor = Color.White.copy(alpha = 0.15f),
                        contentColor = Color.White
                    )
                ) {
                    Text(if (isMapView) "☰" else "🗺", fontSize = 18.sp)
                }

                // Filter button
                BadgedBox(
                    badge = {
                        if (activeFilterCount > 0) {
                            Badge(containerColor = MaterialTheme.colorScheme.tertiary) {
                                Text("$activeFilterCount", fontSize = 9.sp)
                            }
                        }
                    }
                ) {
                    FilledIconButton(
                        onClick = onFilterClick,
                        modifier = Modifier.size(50.dp),
                        shape = RoundedCornerShape(14.dp),
                        colors = IconButtonDefaults.filledIconButtonColors(
                            containerColor = Color.White.copy(alpha = 0.15f),
                            contentColor = Color.White
                        )
                    ) {
                        Text("⚙", fontSize = 18.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun FilterSheetContent(
    uiState: DiscoveryUiState,
    isLoggedIn: Boolean,
    onTemporalSelect: (String?) -> Unit,
    onCategorySelect: (String?) -> Unit,
    onBookmarkedToggle: () -> Unit,
    onGoingToggle: () -> Unit,
    onClear: () -> Unit,
    onApply: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 32.dp)
    ) {
        // Header
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "Filters",
                fontWeight = FontWeight.Bold,
                fontSize = 18.sp,
                color = MaterialTheme.colorScheme.onSurface
            )
            if (uiState.selectedTemporal != null || uiState.selectedCategoryId != null ||
            uiState.bookmarkedOnly || uiState.goingOnly) {
                TextButton(onClick = onClear) {
                    Text("Clear All", color = MaterialTheme.colorScheme.tertiary, fontSize = 13.sp)
                }
            }
        }

        HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.2f))

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            // Quick filters
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    "QUICK FILTERS",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 2.sp,
                    color = MaterialTheme.colorScheme.tertiary
                )
                Row(
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    listOf("today" to "Today", "this_week" to "This Week", "upcoming" to "Upcoming")
                        .forEach { (key, label) ->
                            val selected = uiState.selectedTemporal == key
                            FilterPill(label = label, selected = selected) {
                                onTemporalSelect(key)
                            }
                        }
                    if (isLoggedIn) {
                        FilterPill(
                            label = "🔖 Bookmarked",
                            selected = uiState.bookmarkedOnly,
                            onClick = onBookmarkedToggle
                        )
                        FilterPill(
                            label = "✓ Going",
                            selected = uiState.goingOnly,
                            onClick = onGoingToggle
                        )
                    }
                }
            }

            HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.15f))

            // Categories
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    "CATEGORY",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 2.sp,
                    color = MaterialTheme.colorScheme.tertiary
                )
                uiState.categories.forEach { cat ->
                    val selected = uiState.selectedCategoryId == cat.id
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(10.dp))
                            .clickable { onCategorySelect(cat.id) }
                            .padding(horizontal = 10.dp, vertical = 10.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            cat.name,
                            fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Box(
                            modifier = Modifier
                                .size(20.dp)
                                .clip(RoundedCornerShape(4.dp))
                                .background(
                                    if (selected) MaterialTheme.colorScheme.primary
                                    else MaterialTheme.colorScheme.outline.copy(alpha = 0.2f)
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            if (selected) {
                                Icon(
                                    Icons.Default.Check, null,
                                    tint = MaterialTheme.colorScheme.onPrimary,
                                    modifier = Modifier.size(14.dp)
                                )
                            }
                        }
                    }
                }
            }
        }

        // Apply button
        Button(
            onClick = onApply,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp)
                .height(48.dp),
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.primary
            )
        ) {
            Text("Apply Filters", fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun FilterPill(label: String, selected: Boolean, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(20.dp))
            .background(
                if (selected) MaterialTheme.colorScheme.primary
                else MaterialTheme.colorScheme.outline.copy(alpha = 0.15f)
            )
            .clickable { onClick() }
            .padding(horizontal = 14.dp, vertical = 7.dp)
    ) {
        Text(
            text = label,
            fontSize = 13.sp,
            fontWeight = FontWeight.SemiBold,
            color = if (selected) MaterialTheme.colorScheme.onPrimary
                    else MaterialTheme.colorScheme.onSurface
        )
    }
}

@Composable
fun EventCard(event: EventListItemDto, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable { onClick() },
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column {
            // Image
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(160.dp)
                    .background(MaterialTheme.colorScheme.tertiary.copy(alpha = 0.25f))
            ) {
                if (event.primary_image_url != null) {
                    AsyncImage(
                        model = event.primary_image_url,
                        contentDescription = event.title,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize()
                    )
                } else {
                    Text(
                        "EVENT PHOTO",
                        modifier = Modifier.align(Alignment.Center),
                        color = Color.White.copy(alpha = 0.35f),
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 2.sp
                    )
                }
                Row(
                    modifier = Modifier.align(Alignment.TopEnd).padding(8.dp),
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    if (event.is_full == true) SmallBadge("FULL", Color(0xFFB91C1C))
                    if (event.is_age_restricted) SmallBadge("18+", Color(0xFF1F2937))
                    if (event.visibility == "private") SmallBadgeIcon("PRIVATE", Color(0xFF1F2937))
                }
            }

            Column(modifier = Modifier.padding(12.dp)) {
                Text(
                    event.title,
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp,
                    color = MaterialTheme.colorScheme.onSurface,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(Modifier.height(3.dp))
                Text(
                    formatEventDate(event.start_datetime),
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.tertiary,
                    fontWeight = FontWeight.SemiBold
                )
                if (event.categories.isNotEmpty()) {
                    Spacer(Modifier.height(8.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        event.categories.take(3).forEach { cat ->
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(20.dp))
                                    .background(MaterialTheme.colorScheme.tertiary.copy(alpha = 0.15f))
                                    .padding(horizontal = 10.dp, vertical = 3.dp)
                            ) {
                                Text(cat.name, fontSize = 11.sp, fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onSurface)
                            }
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
                Text(
                    "👥 ${event.going_count}${event.attendee_limit?.let { "/$it" } ?: ""} going",
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun SmallBadge(text: String, color: Color) {
    Box(
        modifier = Modifier.clip(RoundedCornerShape(20.dp)).background(color)
            .padding(horizontal = 8.dp, vertical = 2.dp)
    ) {
        Text(text, color = Color.White, fontSize = 9.sp, fontWeight = FontWeight.ExtraBold)
    }
}

@Composable
private fun SmallBadgeIcon(text: String, color: Color) {
    Row(
        modifier = Modifier.clip(RoundedCornerShape(20.dp)).background(color)
            .padding(horizontal = 8.dp, vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(3.dp)
    ) {
        Icon(Icons.Default.Lock, null, tint = Color.White, modifier = Modifier.size(9.dp))
        Text(text, color = Color.White, fontSize = 9.sp, fontWeight = FontWeight.ExtraBold)
    }
}

fun formatEventDate(dateStr: String): String {
    return try {
        val formats = listOf("yyyy-MM-dd'T'HH:mm:ssXXX", "yyyy-MM-dd'T'HH:mm:ss.SSSXXX",
            "yyyy-MM-dd'T'HH:mm:ssZ", "yyyy-MM-dd'T'HH:mm:ss")
        var date: java.util.Date? = null
        for (fmt in formats) {
            try {
                val sdf = SimpleDateFormat(fmt, Locale.ENGLISH)
                sdf.timeZone = TimeZone.getTimeZone("UTC")
                date = sdf.parse(dateStr)
                break
            } catch (_: Exception) {}
        }
        date?.let { SimpleDateFormat("EEE, MMM d · HH:mm", Locale.ENGLISH).format(it) } ?: dateStr
    } catch (e: Exception) { dateStr }
}
