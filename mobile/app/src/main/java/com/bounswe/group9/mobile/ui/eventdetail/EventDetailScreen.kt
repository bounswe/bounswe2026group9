package com.bounswe.group9.mobile.ui.eventdetail

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.Accessible
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Group
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.BookmarkBorder
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.bounswe.group9.mobile.data.remote.AccessRequestResponseDto
import com.bounswe.group9.mobile.data.remote.EventDetailDto
import com.bounswe.group9.mobile.data.remote.EventListItemDto
import com.bounswe.group9.mobile.data.remote.EventLimitedDto
import com.bounswe.group9.mobile.data.remote.EquipmentDto
import com.bounswe.group9.mobile.data.remote.InviteResponseDto
import com.bounswe.group9.mobile.data.remote.VenueMetadataDto
import com.bounswe.group9.mobile.ui.common.formatEventDate
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
    onBack: () -> Unit,
    onNavigateToHost: (String) -> Unit = {},
    onNavigateToEvent: (String) -> Unit = {},
    onNavigateToEdit: (EventDetailDto) -> Unit = {},
    onDeleteSuccess: () -> Unit = {}
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

    // Confirmation dialog state
    var showCancelDialog by remember { mutableStateOf(false) }
    var showDeleteDialog by remember { mutableStateOf(false) }

    if (showCancelDialog) {
        ConfirmDialog(
            title = "Cancel Event",
            message = "Are you sure you want to cancel this event? This cannot be undone.",
            confirmLabel = "Cancel Event",
            confirmColor = MaterialTheme.colorScheme.error,
            isLoading = uiState.isHostActionLoading,
            onConfirm = {
                viewModel.cancelEvent {
                    showCancelDialog = false
                }
            },
            onDismiss = { showCancelDialog = false }
        )
    }

    if (showDeleteDialog) {
        ConfirmDialog(
            title = "Delete Event",
            message = "Are you sure you want to permanently delete this event?",
            confirmLabel = "Delete",
            confirmColor = MaterialTheme.colorScheme.error,
            isLoading = uiState.isHostActionLoading,
            onConfirm = {
                viewModel.deleteEvent {
                    showDeleteDialog = false
                    onDeleteSuccess()
                }
            },
            onDismiss = { showDeleteDialog = false }
        )
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
            val detail = uiState.fullDetail
            if (token != null && detail != null) {
                if (isHost) {
                    HostActionBottomBar(
                        event = detail,
                        isLoading = uiState.isHostActionLoading,
                        onEdit = { onNavigateToEdit(detail) },
                        onPublish = { viewModel.publishEvent {} },
                        onCancel = { showCancelDialog = true },
                        onDelete = { showDeleteDialog = true }
                    )
                } else if (isActiveEvent) {
                    ActionBottomBar(
                        event = detail,
                        onToggleBookmark = { viewModel.toggleBookmark() },
                        onGoing = { viewModel.setGoing() },
                        onRemoveAttendance = { viewModel.removeAttendance() }
                    )
                }
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
                uiState.detailError is com.bounswe.group9.mobile.data.repository.EventDetailError.NotFound -> NotFoundScreen(onBack = onBack)
                uiState.detailError is com.bounswe.group9.mobile.data.repository.EventDetailError.Underage -> UnderageScreen()
                uiState.detailError is com.bounswe.group9.mobile.data.repository.EventDetailError.DobRequired -> DobRequiredScreen(
                    dobInput = uiState.dobInput,
                    isSubmitting = uiState.dobSubmitting,
                    onDobChange = { viewModel.onDobChange(it) },
                    onSubmit = { viewModel.submitDob() }
                )
                uiState.errorMessage != null -> ErrorState(
                    message = uiState.errorMessage!!,
                    onRetry = { viewModel.loadEvent(eventId, token) }
                )
                uiState.fullDetail != null -> FullDetailContent(
                    event = uiState.fullDetail!!,
                    uiState = uiState,
                    viewModel = viewModel,
                    token = token,
                    currentUserId = currentUserId,
                    isHost = isHost,
                    onNavigateToHost = onNavigateToHost,
                    onNavigateToEvent = onNavigateToEvent
                )
                uiState.limitedPreview != null -> LimitedPreviewContent(
                    event = uiState.limitedPreview!!,
                    token = token,
                    accessRequestStatus = uiState.accessRequestStatus,
                    isRequestingAccess = uiState.isRequestingAccess,
                    onRequestAccess = { viewModel.requestAccess() }
                )
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

@Composable
private fun NotFoundScreen(onBack: () -> Unit) {
    Column(
        Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text("404", fontSize = 72.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        Spacer(Modifier.height(8.dp))
        Text("Event Not Found", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.height(8.dp))
        Text(
            "This event may have been removed or the link is incorrect.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(24.dp))
        Button(onClick = onBack) { Text("Back to Discovery") }
    }
}

@Composable
private fun UnderageScreen() {
    Column(
        Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(Icons.Default.Shield, contentDescription = null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.error)
        Spacer(Modifier.height(16.dp))
        Text("Age Restricted", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        Text(
            "You must be 18 or older to view this event. This restriction is based on your date of birth.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun DobRequiredScreen(
    dobInput: String,
    isSubmitting: Boolean,
    onDobChange: (String) -> Unit,
    onSubmit: () -> Unit
) {
    Column(
        Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(Icons.Default.Shield, contentDescription = null, modifier = Modifier.size(64.dp), tint = Color(0xFFFFA000))
        Spacer(Modifier.height(16.dp))
        Text("Age Verification Required", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        Text(
            "This event is age-restricted. Please enter your date of birth to verify your age.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(24.dp))
        OutlinedTextField(
            value = dobInput,
            onValueChange = onDobChange,
            label = { Text("Date of Birth") },
            placeholder = { Text("YYYY-MM-DD") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(0.7f)
        )
        Spacer(Modifier.height(16.dp))
        Button(
            onClick = onSubmit,
            enabled = dobInput.matches(Regex("\\d{4}-\\d{2}-\\d{2}")) && !isSubmitting
        ) {
            if (isSubmitting) {
                CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onPrimary)
            } else {
                Text("Verify Age")
            }
        }
    }
}

// endregion

// region Limited Preview

@Composable
private fun LimitedPreviewContent(
    event: EventLimitedDto,
    token: String?,
    accessRequestStatus: String?,
    isRequestingAccess: Boolean,
    onRequestAccess: () -> Unit
) {
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(Icons.Default.Lock, contentDescription = null, modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(16.dp))
        Text(event.title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        Text(formatDateRange(event.start_datetime, event.end_datetime),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(12.dp))
        if (event.categories.isNotEmpty()) {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                event.categories.take(3).forEach { cat ->
                    SuggestionChip(onClick = {}, label = { Text(cat.name, fontSize = 12.sp) })
                }
            }
        }
        Spacer(Modifier.height(20.dp))

        // Request Access UI
        when {
            event.visibility == "private" && token != null -> {
                when (accessRequestStatus) {
                    null -> {
                        Button(
                            onClick = onRequestAccess,
                            enabled = !isRequestingAccess,
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.primary
                            )
                        ) {
                            if (isRequestingAccess) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(16.dp),
                                    color = Color.White,
                                    strokeWidth = 2.dp
                                )
                                Spacer(Modifier.width(8.dp))
                            }
                            Icon(Icons.Default.Lock, contentDescription = null,
                                modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("Request Access")
                        }
                    }
                    "pending" -> {
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = MaterialTheme.colorScheme.secondaryContainer,
                            tonalElevation = 2.dp
                        ) {
                            Row(
                                Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(16.dp),
                                    strokeWidth = 2.dp,
                                    color = MaterialTheme.colorScheme.onSecondaryContainer
                                )
                                Text(
                                    "Access Requested — Pending",
                                    color = MaterialTheme.colorScheme.onSecondaryContainer,
                                    fontWeight = FontWeight.Medium
                                )
                            }
                        }
                    }
                    "rejected" -> {
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = MaterialTheme.colorScheme.errorContainer,
                            tonalElevation = 2.dp
                        ) {
                            Row(
                                Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Icon(Icons.Default.Close, contentDescription = null,
                                    tint = MaterialTheme.colorScheme.onErrorContainer,
                                    modifier = Modifier.size(18.dp))
                                Text(
                                    "Access Request Rejected",
                                    color = MaterialTheme.colorScheme.onErrorContainer,
                                    fontWeight = FontWeight.Medium
                                )
                            }
                        }
                    }
                }
            }
            event.visibility == "private" -> {
                Text(
                    "Sign in to request access to this private event.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            event.status == "cancelled" -> {
                Text(
                    "This event has been cancelled.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.error
                )
            }
            else -> {
                Text(
                    "Sign in to view full event details.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

// endregion

// region Full Detail

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun FullDetailContent(
    event: EventDetailDto,
    uiState: EventDetailUiState,
    viewModel: EventDetailViewModel,
    token: String?,
    currentUserId: String?,
    isHost: Boolean,
    onNavigateToHost: (String) -> Unit,
    onNavigateToEvent: (String) -> Unit = {}
) {
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

            // Host link
            Spacer(Modifier.height(16.dp))
            SectionHeader("Host")
            val displayName = uiState.hostUsername?.let { "@$it" } ?: "View host profile"
            Surface(
                onClick = { onNavigateToHost(event.host_id) },
                shape = RoundedCornerShape(8.dp),
                color = MaterialTheme.colorScheme.secondaryContainer
            ) {
                Text(
                    text = displayName,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                    color = MaterialTheme.colorScheme.onSecondaryContainer,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 14.sp
                )
            }

            // Manage Invites (host only)
            if (isHost && event.visibility == "private") {
                Spacer(Modifier.height(16.dp))
                ManageInvitesSection(
                    uiState = uiState,
                    onCreateInvite = { viewModel.createInvite() },
                    onApprove = { id -> viewModel.decideRequest(id, "approved") },
                    onReject = { id -> viewModel.decideRequest(id, "rejected") },
                    onNavigateToProfile = onNavigateToHost
                )
            }

            // Comments
            Spacer(Modifier.height(16.dp))
            CommentSection(
                comments = uiState.comments,
                commentText = uiState.commentText,
                isPosting = uiState.commentPosting,
                isLoading = uiState.commentsLoading,
                errorMessage = uiState.commentsError,
                hasMore = uiState.commentsPage < uiState.commentsTotalPages,
                isAuthenticated = token != null,
                currentUserId = currentUserId,
                hostId = event.host_id,
                isActiveEvent = event.status in listOf("published", "updated"),
                onTextChange = { viewModel.onCommentTextChange(it) },
                onPost = { viewModel.postComment() },
                onDelete = { viewModel.deleteComment(it) },
                onLoadMore = { viewModel.loadMoreComments() },
                onRetry = { viewModel.loadMoreComments() },
                onNavigateToProfile = onNavigateToHost
            )

            // Similar events
            if (uiState.similarEvents.isNotEmpty() || uiState.similarEventsLoading) {
                Spacer(Modifier.height(16.dp))
                SimilarEventsSection(
                    events = uiState.similarEvents,
                    isLoading = uiState.similarEventsLoading,
                    onEventClick = onNavigateToEvent
                )
            }

            Spacer(Modifier.height(32.dp))
        }
    }
}

// endregion

// region Comment Section

@Composable
private fun CommentSection(
    comments: List<com.bounswe.group9.mobile.data.remote.CommentDto>,
    commentText: String,
    isPosting: Boolean,
    isLoading: Boolean,
    errorMessage: String?,
    hasMore: Boolean,
    isAuthenticated: Boolean,
    currentUserId: String?,
    hostId: String,
    isActiveEvent: Boolean,
    onTextChange: (String) -> Unit,
    onPost: () -> Unit,
    onDelete: (String) -> Unit,
    onLoadMore: () -> Unit,
    onRetry: () -> Unit,
    onNavigateToProfile: (String) -> Unit
) {
    SectionHeader("Comments")

    // Comment input (auth only, active events only)
    if (isAuthenticated && isActiveEvent) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = commentText,
                onValueChange = onTextChange,
                placeholder = { Text("Write a comment...", fontSize = 14.sp) },
                modifier = Modifier.weight(1f),
                maxLines = 3,
                textStyle = MaterialTheme.typography.bodyMedium
            )
            Spacer(Modifier.width(8.dp))
            Button(
                onClick = onPost,
                enabled = commentText.isNotBlank() && !isPosting
            ) {
                if (isPosting) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                } else {
                    Text("Post", fontSize = 13.sp)
                }
            }
        }
        Spacer(Modifier.height(12.dp))
    }

    if (errorMessage != null && comments.isEmpty()) {
        Column {
            Text(errorMessage, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.error)
            Spacer(Modifier.height(8.dp))
            TextButton(onClick = onRetry) { Text("Retry") }
        }
    } else if (comments.isEmpty() && !isLoading) {
        Text("No comments yet", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    } else {
        comments.forEach { comment ->
            CommentItem(
                comment = comment,
                canDelete = currentUserId == comment.user.id || currentUserId == hostId,
                onDelete = { onDelete(comment.id) },
                currentUserId = currentUserId,
                hostId = hostId,
                onDeleteReply = { onDelete(it) },
                onNavigateToProfile = onNavigateToProfile
            )
            Spacer(Modifier.height(8.dp))
        }

        if (hasMore) {
            TextButton(onClick = onLoadMore, modifier = Modifier.fillMaxWidth()) {
                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                } else {
                    Text("Load more comments")
                }
            }
        }
    }
}

@Composable
private fun CommentItem(
    comment: com.bounswe.group9.mobile.data.remote.CommentDto,
    canDelete: Boolean,
    onDelete: () -> Unit,
    currentUserId: String? = null,
    hostId: String? = null,
    onDeleteReply: (String) -> Unit = {},
    onNavigateToProfile: (String) -> Unit = {}
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
    ) {
        Column(Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    comment.user.username,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.clickable { onNavigateToProfile(comment.user.id) }
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        formatCommentTime(comment.created_at),
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    if (canDelete) {
                        IconButton(onClick = onDelete, modifier = Modifier.size(28.dp)) {
                            Icon(Icons.Default.Close, contentDescription = "Delete", modifier = Modifier.size(14.dp))
                        }
                    }
                }
            }
            Spacer(Modifier.height(4.dp))
            Text(comment.text, style = MaterialTheme.typography.bodyMedium)

            if (comment.replies.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                comment.replies.forEach { reply ->
                    Row(Modifier.fillMaxWidth()) {
                        Spacer(Modifier.width(12.dp))
                        Card(
                            modifier = Modifier.weight(1f),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                        ) {
                            Column(Modifier.padding(10.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(
                                        reply.user.username,
                                        fontWeight = FontWeight.SemiBold,
                                        fontSize = 12.sp,
                                        color = MaterialTheme.colorScheme.primary,
                                        modifier = Modifier.clickable { onNavigateToProfile(reply.user.id) }
                                    )
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Text(
                                            formatCommentTime(reply.created_at),
                                            fontSize = 10.sp,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                        val canDeleteReply = currentUserId == reply.user.id || currentUserId == hostId
                                        if (canDeleteReply) {
                                            IconButton(onClick = { onDeleteReply(reply.id) }, modifier = Modifier.size(24.dp)) {
                                                Icon(Icons.Default.Close, contentDescription = "Delete reply", modifier = Modifier.size(12.dp))
                                            }
                                        }
                                    }
                                }
                                Spacer(Modifier.height(2.dp))
                                Text(reply.text, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                    Spacer(Modifier.height(4.dp))
                }
            }
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
private fun ManageInvitesSection(
    uiState: EventDetailUiState,
    onCreateInvite: () -> Unit,
    onApprove: (String) -> Unit,
    onReject: (String) -> Unit,
    onNavigateToProfile: (String) -> Unit
) {
    val clipboard = LocalClipboardManager.current

    SectionHeader("Manage Invites")

    // Invite creation
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        OutlinedButton(
            onClick = onCreateInvite,
            enabled = !uiState.isCreatingInvite,
            modifier = Modifier.weight(1f)
        ) {
            if (uiState.isCreatingInvite) {
                CircularProgressIndicator(modifier = Modifier.size(14.dp), strokeWidth = 2.dp)
                Spacer(Modifier.width(6.dp))
            } else {
                Icon(Icons.Default.Link, contentDescription = null, modifier = Modifier.size(14.dp))
                Spacer(Modifier.width(6.dp))
            }
            Text("Generate Invite Link", fontSize = 13.sp)
        }
    }

    // Active invite links
    if (uiState.invites.isNotEmpty()) {
        Spacer(Modifier.height(8.dp))
        uiState.invites.take(3).forEach { invite ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                ),
                shape = RoundedCornerShape(10.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        // App deep link (sem:// scheme) which the recipient opens in-app
                        val appLink = "sem://invite/${invite.event_id}/${invite.token}"
                        Text(
                            text = appLink,
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Text(
                            text = "Uses: ${invite.use_count}${invite.max_uses?.let { "/$it" } ?: ""}",
                            fontSize = 10.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f)
                        )
                    }
                    IconButton(
                        onClick = {
                            val appLink = "sem://invite/${invite.event_id}/${invite.token}"
                            clipboard.setText(AnnotatedString(appLink))
                        },
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(
                            Icons.Default.ContentCopy,
                            contentDescription = "Copy link",
                            modifier = Modifier.size(16.dp),
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }
            Spacer(Modifier.height(4.dp))
        }
    }

    // Pending access requests
    if (uiState.isLoadingInviteSection) {
        Spacer(Modifier.height(8.dp))
        CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
    } else if (uiState.accessRequests.isNotEmpty()) {
        Spacer(Modifier.height(12.dp))
        Text(
            "Pending Access Requests",
            fontSize = 13.sp,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface
        )
        Spacer(Modifier.height(6.dp))
        uiState.accessRequests.forEach { req ->
            AccessRequestRow(
                request = req,
                onApprove = { onApprove(req.id) },
                onReject = { onReject(req.id) },
                onNavigateToProfile = onNavigateToProfile
            )
            Spacer(Modifier.height(4.dp))
        }
    } else {
        Spacer(Modifier.height(8.dp))
        Text(
            "No pending access requests",
            fontSize = 13.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun AccessRequestRow(
    request: AccessRequestResponseDto,
    onApprove: () -> Unit,
    onReject: () -> Unit,
    onNavigateToProfile: (String) -> Unit = {}
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(10.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                request.username,
                fontWeight = FontWeight.Medium,
                fontSize = 14.sp,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier
                    .weight(1f)
                    .clickable { onNavigateToProfile(request.user_id) }
            )
            Spacer(Modifier.width(8.dp))
            // Approve button
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(Color(0xFF16A34A).copy(alpha = 0.12f))
                    .clickable { onApprove() },
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Default.Check,
                    contentDescription = "Approve",
                    tint = Color(0xFF16A34A),
                    modifier = Modifier.size(18.dp)
                )
            }
            Spacer(Modifier.width(6.dp))
            // Reject button
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(MaterialTheme.colorScheme.errorContainer)
                    .clickable { onReject() },
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Default.Close,
                    contentDescription = "Reject",
                    tint = MaterialTheme.colorScheme.onErrorContainer,
                    modifier = Modifier.size(18.dp)
                )
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

@Composable
private fun SimilarEventsSection(
    events: List<EventListItemDto>,
    isLoading: Boolean,
    onEventClick: (String) -> Unit
) {
    SectionHeader("Similar Events")
    if (isLoading && events.isEmpty()) {
        Box(Modifier.fillMaxWidth().height(140.dp), contentAlignment = Alignment.Center) {
            CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
        }
        return
    }
    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = PaddingValues(end = 4.dp)
    ) {
        items(events) { event ->
            SimilarEventCard(event = event, onClick = { onEventClick(event.id) })
        }
    }
}

@Composable
private fun SimilarEventCard(
    event: EventListItemDto,
    onClick: () -> Unit
) {
    Card(
        onClick = onClick,
        modifier = Modifier.width(180.dp).height(200.dp),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(90.dp)
                    .background(MaterialTheme.colorScheme.tertiary.copy(alpha = 0.2f))
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
            Column(Modifier.padding(horizontal = 10.dp, vertical = 8.dp)) {
                Text(
                    event.title,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 13.sp,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    formatEventDate(event.start_datetime),
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.tertiary,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                if (event.categories.isNotEmpty()) {
                    Spacer(Modifier.height(2.dp))
                    Text(
                        event.categories.first().name,
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        }
    }
}

// endregion

// region Helpers

private fun formatDateRange(start: String, end: String): String {
    return try {
        // Backend returns RFC 3339 / ISO 8601 with timezone offset
        // (e.g. 2026-04-15T14:30:00+00:00 or 2026-04-15T14:30:00Z).
        // The "XXX" pattern reads the embedded offset — do NOT override the
        // parser timezone or it will shift the instant incorrectly.
        // Display formatters use the device default timezone (local time).
        val parser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
        val display = SimpleDateFormat("EEE, MMM d · HH:mm", Locale.getDefault())
        display.timeZone = TimeZone.getDefault()
        val displayEnd = SimpleDateFormat("HH:mm", Locale.getDefault())
        displayEnd.timeZone = TimeZone.getDefault()
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

private fun formatCommentTime(iso: String): String {
    return try {
        // Backend returns RFC 3339 / ISO 8601 with timezone offset.
        // Do NOT override the parser timezone; let "XXX" read the offset.
        val parser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
        val display = SimpleDateFormat("MMM d, HH:mm", Locale.getDefault())
        display.timeZone = TimeZone.getDefault()
        val date = parser.parse(iso)
        if (date != null) display.format(date) else iso
    } catch (_: Exception) {
        iso
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

// region Host Action Bottom Bar

@Composable
private fun HostActionBottomBar(
    event: EventDetailDto,
    isLoading: Boolean,
    onEdit: () -> Unit,
    onPublish: () -> Unit,
    onCancel: () -> Unit,
    onDelete: () -> Unit
) {
    val status = event.status.lowercase()

    Surface(tonalElevation = 3.dp, shadowElevation = 8.dp) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            if (isLoading) {
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Edit — available for all active events
                if (status != "cancelled" && status != "ended") {
                    OutlinedButton(
                        onClick = onEdit,
                        modifier = Modifier.weight(1f),
                        enabled = !isLoading
                    ) {
                        Text("Edit", fontSize = 13.sp)
                    }
                }

                // Publish — only for draft events
                if (status == "draft") {
                    Button(
                        onClick = onPublish,
                        modifier = Modifier.weight(1f),
                        enabled = !isLoading
                    ) {
                        Text("Publish", fontSize = 13.sp)
                    }
                }

                // Cancel — available for all non-draft active events
                if (status != "draft" && status != "cancelled" && status != "ended") {
                    Button(
                        onClick = onCancel,
                        modifier = Modifier.weight(1f),
                        enabled = !isLoading,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.error
                        )
                    ) {
                        Text("Cancel Event", fontSize = 13.sp)
                    }
                }

                // Delete — only for cancelled or ended events
                if (status == "cancelled" || status == "ended") {
                    Button(
                        onClick = onDelete,
                        modifier = Modifier.weight(1f),
                        enabled = !isLoading,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.error
                        )
                    ) {
                        Text("Delete", fontSize = 13.sp)
                    }
                }
            }
        }
    }
}

// endregion

// region Confirmation Dialog

@Composable
private fun ConfirmDialog(
    title: String,
    message: String,
    confirmLabel: String,
    confirmColor: Color,
    isLoading: Boolean,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = { if (!isLoading) onDismiss() },
        title = { Text(title, fontWeight = FontWeight.Bold) },
        text = { Text(message) },
        confirmButton = {
            Button(
                onClick = onConfirm,
                enabled = !isLoading,
                colors = ButtonDefaults.buttonColors(containerColor = confirmColor)
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        strokeWidth = 2.dp,
                        color = Color.White
                    )
                } else {
                    Text(confirmLabel)
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, enabled = !isLoading) {
                Text("Cancel")
            }
        }
    )
}

// endregion