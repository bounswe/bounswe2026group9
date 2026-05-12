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
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
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
import com.bounswe.group9.mobile.ui.common.formatEventDate
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Looper
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.core.content.ContextCompat

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DiscoveryScreen(
    viewModel: DiscoveryViewModel,
    token: String?,
    onEventClick: (String) -> Unit,
    onLoginClick: () -> Unit = {},
    onLogout: () -> Unit = {},
    username: String? = null,
    unreadNotificationCount: Int = 0,
    onNotificationsClick: () -> Unit = {},
    onProfileClick: () -> Unit = {},
    onCreateEvent: () -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsState()
    val listState = rememberLazyListState()
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val scope = rememberCoroutineScope()
    var showFilterSheet by remember { mutableStateOf(false) }
    var isMapView by remember { mutableStateOf(true) } // default: map
    var locationPermissionDenied by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val snackbarHostState = remember { SnackbarHostState() }

    val locationPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            viewModel.enableProximitySortOptimistic()
            requestCurrentLocation(context) { loc ->
                if (loc != null) viewModel.enableProximitySort(loc.first, loc.second)
                else {
                    viewModel.revertProximitySort()
                    scope.launch { snackbarHostState.showSnackbar("Could not get location. Try again.") }
                }
            }
        } else {
            locationPermissionDenied = true
            scope.launch { snackbarHostState.showSnackbar("Location permission denied. Cannot use proximity ranking.") }
        }
    }

    LaunchedEffect(token) { viewModel.setToken(token) }

    // Infinite scroll
    LaunchedEffect(listState.firstVisibleItemIndex, uiState.events.size) {
        val lastVisible = listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0
        if (lastVisible >= uiState.events.size - 4 && !uiState.isLoadingMore) {
            viewModel.loadNextPage()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        floatingActionButton = {
            if (token != null) {
                ExtendedFloatingActionButton(
                    onClick = onCreateEvent,
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
                onViewToggle = { isMapView = !isMapView },
                unreadNotificationCount = unreadNotificationCount,
                onNotificationsClick = onNotificationsClick,
                onProfileClick = onProfileClick
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            // Empty-history hint for the Suggested filter (issue #277). Shown above the listing
            // whenever the chip is on AND the server signalled it had no history to bias by.
            if (uiState.suggestedActive && uiState.suggestedFallback) {
                val bannerText = when (uiState.suggestedFallbackReason) {
                    "no_match" -> "No events matching your interests right now. Showing default results."
                    else -> "Attend events to get personalised suggestions. Showing default results."
                }
                Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.secondaryContainer
                ) {
                    Text(
                        bannerText,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSecondaryContainer
                    )
                }
            }
            // Map is always in composition — switching tabs or reloading data
            // never destroys the MapLibre view (only visibility toggles).
            PullToRefreshBox(
                isRefreshing = uiState.isLoading,
                onRefresh = { viewModel.refresh() },
                modifier = Modifier.fillMaxSize().weight(1f)
            ) {
                // Map: always composed, visibility driven by visible= param
                val showMap = isMapView && !uiState.isLoading && uiState.errorMessage == null
                EventMapView(
                    events = uiState.displayedEvents,
                    onEventClick = onEventClick,
                    onBookmarkToggle = { eventId -> viewModel.toggleBookmark(eventId) },
                    token = token,
                    visible = showMap,
                    onRefresh = { viewModel.refresh() }
                )

                when {
                    uiState.isLoading -> {
                        LazyColumn(
                            contentPadding = PaddingValues(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            items(5) { EventCardSkeleton() }
                        }
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
                    isMapView -> { /* map is visible, nothing to overlay */ }
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
                onQuickFilterSelect = viewModel::onQuickFilterSelected,
                onCategoryToggle = viewModel::onCategoryToggled,
                onSortSelect = viewModel::onSortSelected,
                onBookmarkedToggle = viewModel::onBookmarkedOnlyToggle,
                onGoingToggle = viewModel::onGoingOnlyToggle,
                onWheelchairToggle = viewModel::onWheelchairToggle,
                onAccessibleRestroomToggle = viewModel::onAccessibleRestroomToggle,
                onElevatorToggle = viewModel::onElevatorToggle,
                onSeatingToggle = viewModel::onSeatingToggle,
                onCaptionsToggle = viewModel::onCaptionsToggle,
                onQuietFriendlyToggle = viewModel::onQuietFriendlyToggle,
                onSuggestedToggle = viewModel::onSuggestedToggle,
                onProximitySortToggle = {
                    if (uiState.proximitySort) {
                        viewModel.disableProximitySort()
                    } else {
                        val hasPermission = ContextCompat.checkSelfPermission(
                            context, Manifest.permission.ACCESS_FINE_LOCATION
                        ) == PackageManager.PERMISSION_GRANTED
                        if (hasPermission) {
                            viewModel.enableProximitySortOptimistic()
                            requestCurrentLocation(context) { loc ->
                                if (loc != null) viewModel.enableProximitySort(loc.first, loc.second)
                                else {
                                    viewModel.revertProximitySort()
                                    scope.launch { snackbarHostState.showSnackbar("Could not get location. Try again.") }
                                }
                            }
                        } else {
                            locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
                        }
                    }
                },
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
    onViewToggle: () -> Unit,
    unreadNotificationCount: Int = 0,
    onNotificationsClick: () -> Unit = {},
    onProfileClick: () -> Unit = {}
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
                    if (isLoggedIn) {
                        // Bell icon with unread badge
                        Box(modifier = Modifier.size(34.dp)) {
                            IconButton(
                                onClick = onNotificationsClick,
                                modifier = Modifier.size(34.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Notifications,
                                    contentDescription = "Notifications",
                                    tint = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.85f),
                                    modifier = Modifier.size(22.dp)
                                )
                            }
                            if (unreadNotificationCount > 0) {
                                Box(
                                    modifier = Modifier
                                        .align(Alignment.TopEnd)
                                        .size(16.dp)
                                        .clip(RoundedCornerShape(50))
                                        .background(Color(0xFFE53935)),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(
                                        text = if (unreadNotificationCount > 9) "9+" else "$unreadNotificationCount",
                                        color = Color.White,
                                        fontSize = 8.sp,
                                        fontWeight = FontWeight.Bold,
                                        lineHeight = 8.sp
                                    )
                                }
                            }
                        }
                    }
                    if (isLoggedIn && username != null) {
                        Box(
                            modifier = Modifier
                                .size(34.dp)
                                .clip(RoundedCornerShape(50))
                                .background(MaterialTheme.colorScheme.tertiary)
                                .clickable { onProfileClick() },
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
                    } else if (isLoggedIn) {
                        // Token exists but username still loading — show placeholder avatar
                        Box(
                            modifier = Modifier
                                .size(34.dp)
                                .clip(RoundedCornerShape(50))
                                .background(MaterialTheme.colorScheme.tertiary.copy(alpha = 0.5f))
                                .clickable { onProfileClick() },
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(16.dp),
                                strokeWidth = 2.dp,
                                color = Color.White
                            )
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
                    placeholder = { Text("Search events or places...", fontSize = 13.sp, color = Color.White.copy(alpha = 0.5f)) },
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
                    modifier = Modifier.size(50.dp).semantics {
                        contentDescription = if (isMapView) "Switch to List View" else "Switch to Map View"
                    },
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
                        modifier = Modifier.size(50.dp).semantics { contentDescription = "Open Filters" },
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
    onQuickFilterSelect: (String?) -> Unit,
    onCategoryToggle: (String) -> Unit,
    onBookmarkedToggle: () -> Unit,
    onGoingToggle: () -> Unit,
    onWheelchairToggle: () -> Unit,
    onAccessibleRestroomToggle: () -> Unit,
    onElevatorToggle: () -> Unit,
    onSeatingToggle: () -> Unit,
    onCaptionsToggle: () -> Unit,
    onQuietFriendlyToggle: () -> Unit,
    onSuggestedToggle: () -> Unit,
    onProximitySortToggle: () -> Unit,
    onSortSelect: (String?) -> Unit,
    onClear: () -> Unit,
    onApply: () -> Unit
) {
    val hasAnyFilter = uiState.selectedQuickFilter != null || uiState.selectedCategoryIds.isNotEmpty() ||
        uiState.bookmarkedOnly || uiState.goingOnly || uiState.hasAccessibilityFilter ||
        uiState.proximitySort || uiState.suggestedActive || uiState.selectedSort != null

    Column(modifier = Modifier.fillMaxWidth().padding(bottom = 32.dp)) {
        // Header
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Filters", fontWeight = FontWeight.Bold, fontSize = 18.sp,
                color = MaterialTheme.colorScheme.onSurface)
            if (hasAnyFilter) {
                TextButton(onClick = onClear) {
                    Text("Clear All", color = MaterialTheme.colorScheme.tertiary, fontSize = 13.sp)
                }
            }
        }

        HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.2f))

        Column(
            modifier = Modifier.fillMaxWidth().weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            FilterQuickFiltersSection(uiState, isLoggedIn, onQuickFilterSelect,
                onBookmarkedToggle, onGoingToggle, onSuggestedToggle)
            HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.15f))
            FilterSortSection(uiState, onSortSelect)
            HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.15f))
            FilterSectionLabel("RANKING")
            FilterSwitchRow(
                label = "Proximity Ranking",
                sublabel = "Sort by distance from your current location",
                checked = uiState.proximitySort,
                onCheckedChange = { onProximitySortToggle() }
            )
            HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.15f))
            FilterAccessibilitySection(uiState, onWheelchairToggle, onAccessibleRestroomToggle,
                onElevatorToggle, onSeatingToggle, onCaptionsToggle, onQuietFriendlyToggle)
            HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.15f))
            FilterCategorySection(uiState, onCategoryToggle)
        }

        Button(
            onClick = onApply,
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp).height(48.dp),
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
        ) {
            Text("Apply Filters", fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun FilterQuickFiltersSection(
    uiState: DiscoveryUiState,
    isLoggedIn: Boolean,
    onQuickFilterSelect: (String?) -> Unit,
    onBookmarkedToggle: () -> Unit,
    onGoingToggle: () -> Unit,
    onSuggestedToggle: () -> Unit
) {
    FilterSectionLabel("QUICK FILTERS")
    Row(
        modifier = Modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        if (isLoggedIn) FilterPill("✨ Suggested for you", uiState.suggestedActive, onSuggestedToggle)
        listOf("now" to "Now", "today" to "Today", "weekend" to "Weekend",
            "this_week" to "This Week", "upcoming" to "Upcoming", "past" to "Past"
        ).forEach { (key, label) ->
            FilterPill(label = label, selected = uiState.selectedQuickFilter == key) {
                onQuickFilterSelect(key)
            }
        }
        if (isLoggedIn) {
            FilterPill("🔖 Bookmarked", uiState.bookmarkedOnly, onBookmarkedToggle)
            FilterPill("✓ Going", uiState.goingOnly, onGoingToggle)
        }
    }
}

@Composable
private fun FilterSortSection(uiState: DiscoveryUiState, onSortSelect: (String?) -> Unit) {
    FilterSectionLabel("SORT BY")
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        listOf("start_time" to "Start Time", "category" to "Category").forEach { (key, label) ->
            FilterPill(
                label = label,
                selected = uiState.selectedSort == key && !uiState.proximitySort
            ) { onSortSelect(if (uiState.selectedSort == key) null else key) }
        }
    }
}

@Composable
private fun FilterAccessibilitySection(
    uiState: DiscoveryUiState,
    onWheelchairToggle: () -> Unit,
    onAccessibleRestroomToggle: () -> Unit,
    onElevatorToggle: () -> Unit,
    onSeatingToggle: () -> Unit,
    onCaptionsToggle: () -> Unit,
    onQuietFriendlyToggle: () -> Unit
) {
    FilterSectionLabel("ACCESSIBILITY")
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        FilterSwitchRow("Wheelchair Access", checked = uiState.wheelchair,
            onCheckedChange = { onWheelchairToggle() })
        FilterSwitchRow("Accessible Restroom", checked = uiState.accessibleRestroom,
            onCheckedChange = { onAccessibleRestroomToggle() })
        FilterSwitchRow("Elevator Available", checked = uiState.elevator,
            onCheckedChange = { onElevatorToggle() })
        FilterSwitchRow("Seating Available", checked = uiState.seating,
            onCheckedChange = { onSeatingToggle() })
        FilterSwitchRow("Captions Support", checked = uiState.captions,
            onCheckedChange = { onCaptionsToggle() })
        FilterSwitchRow("Quiet-Friendly", checked = uiState.quietFriendly,
            onCheckedChange = { onQuietFriendlyToggle() })
    }
}

@Composable
private fun FilterCategorySection(uiState: DiscoveryUiState, onCategoryToggle: (String) -> Unit) {
    FilterSectionLabel("CATEGORY")
    uiState.categories.forEach { cat ->
        val selected = cat.id in uiState.selectedCategoryIds
        Row(
            modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp))
                .clickable { onCategoryToggle(cat.id) }
                .padding(horizontal = 10.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(cat.name, fontSize = 14.sp, color = MaterialTheme.colorScheme.onSurface)
            Box(
                modifier = Modifier.size(20.dp).clip(RoundedCornerShape(4.dp))
                    .background(
                        if (selected) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.outline.copy(alpha = 0.2f)
                    ),
                contentAlignment = Alignment.Center
            ) {
                if (selected) Icon(Icons.Default.Check, null,
                    tint = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(14.dp))
            }
        }
    }
}

@Composable
private fun FilterSectionLabel(text: String) {
    Text(
        text,
        fontSize = 10.sp,
        fontWeight = FontWeight.Bold,
        letterSpacing = 2.sp,
        color = MaterialTheme.colorScheme.tertiary
    )
}

@Composable
private fun FilterSwitchRow(
    label: String,
    sublabel: String? = null,
    checked: Boolean,
    enabled: Boolean = true,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(label, fontSize = 14.sp, color = if (enabled) MaterialTheme.colorScheme.onSurface
                 else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f))
            if (sublabel != null) {
                Text(sublabel, fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = if (enabled) 1f else 0.4f))
            }
        }
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            enabled = enabled,
            colors = SwitchDefaults.colors(
                checkedThumbColor = MaterialTheme.colorScheme.onPrimary,
                checkedTrackColor = MaterialTheme.colorScheme.primary
            )
        )
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

/** Requests a fresh location fix and delivers (lat, lng) via [onResult], or null on failure. */
private fun requestCurrentLocation(context: Context, onResult: (Pair<Double, Double>?) -> Unit) {
    val lm = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
    val provider = when {
        lm.isProviderEnabled(LocationManager.GPS_PROVIDER) &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) ==
                PackageManager.PERMISSION_GRANTED -> LocationManager.GPS_PROVIDER
        lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER) &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) ==
                PackageManager.PERMISSION_GRANTED -> LocationManager.NETWORK_PROVIDER
        else -> null
    }
    if (provider == null) { onResult(null); return }
    @Suppress("MissingPermission")
    lm.requestSingleUpdate(provider, object : LocationListener {
        override fun onLocationChanged(loc: Location) = onResult(Pair(loc.latitude, loc.longitude))
        override fun onProviderDisabled(p: String) = onResult(null)
        override fun onStatusChanged(p: String?, s: Int, e: Bundle?) {}
    }, Looper.getMainLooper())
}

@Composable
fun EventCardSkeleton() {
    val shimmerColors = listOf(
        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.2f),
        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
    )
    val transition = rememberInfiniteTransition(label = "shimmer")
    val translateAnim by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1000f,
        animationSpec = infiniteRepeatable(tween(800)),
        label = "shimmer_offset"
    )
    val brush = Brush.linearGradient(
        colors = shimmerColors,
        start = Offset(translateAnim - 200f, translateAnim - 200f),
        end = Offset(translateAnim, translateAnim)
    )

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column {
            Box(modifier = Modifier.fillMaxWidth().height(160.dp).background(brush))
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Box(modifier = Modifier.fillMaxWidth(0.7f).height(16.dp).clip(RoundedCornerShape(4.dp)).background(brush))
                Box(modifier = Modifier.fillMaxWidth(0.4f).height(12.dp).clip(RoundedCornerShape(4.dp)).background(brush))
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    repeat(2) {
                        Box(modifier = Modifier.width(60.dp).height(20.dp).clip(RoundedCornerShape(20.dp)).background(brush))
                    }
                }
                Box(modifier = Modifier.fillMaxWidth(0.3f).height(12.dp).clip(RoundedCornerShape(4.dp)).background(brush))
            }
        }
    }
}