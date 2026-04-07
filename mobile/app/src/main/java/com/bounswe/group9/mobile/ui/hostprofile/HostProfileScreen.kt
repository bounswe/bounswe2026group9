package com.bounswe.group9.mobile.ui.hostprofile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.bounswe.group9.mobile.data.remote.EventListItemDto
import com.bounswe.group9.mobile.ui.common.formatEventDate

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HostProfileScreen(
    viewModel: HostProfileViewModel,
    userId: String,
    token: String?,
    currentUserId: String?,
    onBack: () -> Unit,
    onEventClick: (String) -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(userId, token) {
        viewModel.loadProfile(userId, token)
    }

    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(uiState.actionError) {
        uiState.actionError?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearActionError()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Host Profile", maxLines = 1, overflow = TextOverflow.Ellipsis) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { padding ->
        Box(
            modifier = Modifier.fillMaxSize().padding(padding)
        ) {
            when {
                uiState.isLoading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
                uiState.errorMessage != null -> Column(
                    Modifier.fillMaxSize().padding(32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Icon(Icons.Default.Info, contentDescription = null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.error)
                    Spacer(Modifier.height(16.dp))
                    Text("Could not load profile", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(8.dp))
                    Text(uiState.errorMessage!!, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.height(24.dp))
                    Button(onClick = { viewModel.loadProfile(userId, token) }) { Text("Retry") }
                }
                uiState.profile != null -> ProfileContent(
                    profile = uiState.profile!!,
                    uiState = uiState,
                    isOwnProfile = currentUserId == userId,
                    isAuthenticated = token != null,
                    onRatingChange = { viewModel.onRatingChange(it) },
                    onSubmitRating = { viewModel.submitRating(userId) },
                    onEventClick = onEventClick
                )
            }
        }
    }
}

@Composable
private fun ProfileContent(
    profile: com.bounswe.group9.mobile.data.remote.HostProfileDto,
    uiState: HostProfileUiState,
    isOwnProfile: Boolean,
    isAuthenticated: Boolean,
    onRatingChange: (Double) -> Unit,
    onSubmitRating: () -> Unit,
    onEventClick: (String) -> Unit
) {
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        // Avatar + Name
        Row(verticalAlignment = Alignment.CenterVertically) {
            Surface(
                shape = RoundedCornerShape(50),
                color = MaterialTheme.colorScheme.primaryContainer,
                modifier = Modifier.size(64.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(Icons.Default.Person, contentDescription = null, modifier = Modifier.size(32.dp))
                }
            }
            Spacer(Modifier.width(16.dp))
            Column {
                Text(profile.username, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text("${profile.hosted_events_count} events hosted", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }

        Spacer(Modifier.height(16.dp))

        // Rating
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp)) {
                Text("Rating", fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
                Spacer(Modifier.height(8.dp))
                if (profile.average_rating != null) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        repeat(5) { i ->
                            Icon(
                                Icons.Default.Star,
                                contentDescription = null,
                                modifier = Modifier.size(20.dp),
                                tint = if (i < profile.average_rating.toInt()) Color(0xFFFFC107) else Color(0xFF9E9E9E)
                            )
                        }
                        Spacer(Modifier.width(8.dp))
                        Text("${String.format("%.1f", profile.average_rating)}", fontWeight = FontWeight.Medium)
                    }
                } else {
                    Text("No ratings yet", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }

                // Rate this host (auth only, not own profile)
                if (isAuthenticated && !isOwnProfile) {
                    Spacer(Modifier.height(12.dp))
                    Text("Rate this host", fontSize = 14.sp, fontWeight = FontWeight.Medium)
                    Spacer(Modifier.height(4.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        repeat(5) { i ->
                            IconButton(
                                onClick = { onRatingChange((i + 1).toDouble()) },
                                modifier = Modifier.size(36.dp)
                            ) {
                                Icon(
                                    Icons.Default.Star,
                                    contentDescription = "Rate ${i + 1}",
                                    tint = if (i < uiState.ratingScore.toInt()) Color(0xFFFFC107) else Color(0xFF9E9E9E),
                                    modifier = Modifier.size(24.dp)
                                )
                            }
                        }
                        Spacer(Modifier.width(8.dp))
                        Button(
                            onClick = onSubmitRating,
                            enabled = !uiState.ratingSubmitting
                        ) {
                            if (uiState.ratingSubmitting) {
                                CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                            } else {
                                Text(if (uiState.ratingSuccess) "Updated" else "Submit", fontSize = 13.sp)
                            }
                        }
                    }
                }
            }
        }

        // Contact info
        if (profile.email != null || profile.phone_number != null) {
            Spacer(Modifier.height(16.dp))
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text("Contact", fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
                    Spacer(Modifier.height(8.dp))
                    profile.email?.let {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Email, contentDescription = null, modifier = Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                            Spacer(Modifier.width(8.dp))
                            Text(it, style = MaterialTheme.typography.bodyMedium)
                        }
                        Spacer(Modifier.height(4.dp))
                    }
                    profile.phone_number?.let {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Phone, contentDescription = null, modifier = Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                            Spacer(Modifier.width(8.dp))
                            Text(it, style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
        }

        // Hosted events
        Spacer(Modifier.height(16.dp))
        Text("Hosted Events", fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
        Spacer(Modifier.height(8.dp))

        if (profile.hosted_events.isEmpty()) {
            Text("No events hosted yet", color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            profile.hosted_events.forEach { event ->
                HostedEventCard(event = event, onClick = { onEventClick(event.id) })
                Spacer(Modifier.height(8.dp))
            }
        }

        Spacer(Modifier.height(32.dp))
    }
}

@Composable
private fun HostedEventCard(event: EventListItemDto, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(12.dp)) {
            Text(event.title, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Spacer(Modifier.height(4.dp))
            Text(
                formatEventDate(event.start_datetime),
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.height(4.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Surface(
                    shape = RoundedCornerShape(4.dp),
                    color = when (event.status) {
                        "ended" -> MaterialTheme.colorScheme.surfaceVariant
                        "cancelled" -> MaterialTheme.colorScheme.errorContainer
                        else -> MaterialTheme.colorScheme.primaryContainer
                    }
                ) {
                    Text(
                        event.status.replaceFirstChar { it.uppercase() },
                        fontSize = 11.sp,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                    )
                }
                Text("${event.going_count} going", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

