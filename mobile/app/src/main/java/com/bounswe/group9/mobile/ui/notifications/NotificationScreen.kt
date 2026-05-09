package com.bounswe.group9.mobile.ui.notifications

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.PersonAdd
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.repeatOnLifecycle
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.bounswe.group9.mobile.data.remote.NotificationDto
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationScreen(
    viewModel: NotificationViewModel,
    token: String?,
    onBack: () -> Unit,
    onEventClick: (String) -> Unit = {}
) {
    val uiState by viewModel.uiState.collectAsState()
    val listState = rememberLazyListState()

    LaunchedEffect(token) { viewModel.setToken(token) }

    val lifecycleOwner = LocalLifecycleOwner.current
    LaunchedEffect(lifecycleOwner) {
        lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.RESUMED) {
            viewModel.refresh()
        }
    }

    // Pagination
    LaunchedEffect(listState.firstVisibleItemIndex, uiState.notifications.size) {
        val lastVisible = listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0
        if (lastVisible >= uiState.notifications.size - 3 && !uiState.isLoadingMore) {
            viewModel.loadNextPage()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            "Notifications",
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Light,
                            color = MaterialTheme.colorScheme.onPrimary
                        )
                        if (uiState.unreadCount > 0) {
                            Spacer(Modifier.width(8.dp))
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(MaterialTheme.colorScheme.tertiary)
                                    .padding(horizontal = 6.dp, vertical = 2.dp)
                            ) {
                                Text(
                                    text = "${uiState.unreadCount}",
                                    color = Color.White,
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = MaterialTheme.colorScheme.onPrimary
                        )
                    }
                },
                actions = {
                    if (uiState.notifications.any { !it.is_read }) {
                        if (uiState.isMarkingAllRead) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp).padding(end = 16.dp),
                                color = MaterialTheme.colorScheme.onPrimary,
                                strokeWidth = 2.dp
                            )
                        } else {
                            TextButton(onClick = viewModel::markAllAsRead) {
                                Text(
                                    "Mark all read",
                                    color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.85f),
                                    fontSize = 12.sp
                                )
                            }
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary
                )
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = uiState.isLoading,
            onRefresh = { viewModel.refresh() },
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
                    Column(
                        modifier = Modifier.align(Alignment.Center).padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            "Something went wrong",
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            uiState.errorMessage ?: "",
                            color = MaterialTheme.colorScheme.error,
                            fontSize = 12.sp
                        )
                        Spacer(Modifier.height(8.dp))
                        TextButton(onClick = viewModel::refresh) {
                            Text("Retry", color = MaterialTheme.colorScheme.tertiary)
                        }
                    }
                }
                uiState.notifications.isEmpty() -> {
                    Column(
                        modifier = Modifier.align(Alignment.Center).padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            Icons.Default.Notifications,
                            contentDescription = null,
                            modifier = Modifier.size(48.dp),
                            tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f)
                        )
                        Spacer(Modifier.height(12.dp))
                        Text(
                            "No notifications yet",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
                else -> {
                    LazyColumn(
                        state = listState,
                        contentPadding = PaddingValues(vertical = 8.dp)
                    ) {
                        items(uiState.notifications, key = { it.id }) { notification ->
                            NotificationCard(
                                notification = notification,
                                onMarkRead = {
                                    if (!notification.is_read) viewModel.markAsRead(notification.id)
                                },
                                onNavigate = {
                                    // Mark as read then navigate to related event
                                    if (!notification.is_read) viewModel.markAsRead(notification.id)
                                    notification.event_id?.let { onEventClick(it) }
                                }
                            )
                            HorizontalDivider(
                                color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f),
                                thickness = 0.5.dp
                            )
                        }
                        if (uiState.isLoadingMore) {
                            item {
                                Box(
                                    Modifier.fillMaxWidth().padding(16.dp),
                                    Alignment.Center
                                ) {
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

@Composable
private fun NotificationCard(
    notification: NotificationDto,
    onMarkRead: () -> Unit,
    onNavigate: () -> Unit = {}
) {
    val unreadBg = MaterialTheme.colorScheme.tertiary.copy(alpha = 0.06f)
    val readBg = Color.Transparent
    val hasEvent = notification.event_id != null

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(if (!notification.is_read) unreadBg else readBg)
            .clickable {
                onMarkRead()
                if (hasEvent) onNavigate()
            }
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.Top
    ) {
        // Type icon
        Box(
            modifier = Modifier
                .size(38.dp)
                .clip(CircleShape)
                .background(notificationIconBg(notification.type, notification.is_read)),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = notificationIcon(notification.type),
                contentDescription = null,
                tint = notificationIconTint(notification.type, notification.is_read),
                modifier = Modifier.size(20.dp)
            )
        }

        Spacer(Modifier.width(12.dp))

        // Content
        Column(modifier = Modifier.weight(1f)) {
            if (notification.type == "event_recommended") {
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = MaterialTheme.colorScheme.primaryContainer
                ) {
                    Text(
                        text = "Recommended for you",
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                        fontSize = 10.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                }
                Spacer(Modifier.height(4.dp))
            }
            Text(
                text = notification.message,
                fontSize = 14.sp,
                fontWeight = if (!notification.is_read) FontWeight.SemiBold else FontWeight.Normal,
                color = MaterialTheme.colorScheme.onBackground,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = formatNotificationDate(notification.created_at),
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        // Unread dot
        if (!notification.is_read) {
            Spacer(Modifier.width(8.dp))
            Box(
                modifier = Modifier
                    .padding(top = 4.dp)
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.tertiary)
            )
        }
    }
}

private fun notificationIcon(type: String): ImageVector = when (type) {
    "event_updated" -> Icons.Default.Edit
    "event_cancelled", "event_deleted" -> Icons.Default.Cancel
    "access_request" -> Icons.Default.PersonAdd
    "access_approved" -> Icons.Default.CheckCircle
    "access_rejected" -> Icons.Default.Cancel
    "event_recommended" -> Icons.Default.AutoAwesome
    else -> Icons.Default.Notifications
}

@Composable
private fun notificationIconBg(type: String, isRead: Boolean): Color {
    val alpha = if (isRead) 0.08f else 0.15f
    return when (type) {
        "event_updated" -> MaterialTheme.colorScheme.tertiary.copy(alpha = alpha)
        "event_cancelled", "event_deleted", "access_rejected" ->
            MaterialTheme.colorScheme.error.copy(alpha = alpha)
        "access_approved" -> Color(0xFF4CAF50).copy(alpha = alpha)
        "event_recommended" -> MaterialTheme.colorScheme.primary.copy(alpha = alpha)
        else -> MaterialTheme.colorScheme.tertiary.copy(alpha = alpha)
    }
}

@Composable
private fun notificationIconTint(type: String, isRead: Boolean): Color {
    val alpha = if (isRead) 0.5f else 1f
    return when (type) {
        "event_cancelled", "event_deleted", "access_rejected" ->
            MaterialTheme.colorScheme.error.copy(alpha = alpha)
        "access_approved" -> Color(0xFF4CAF50).copy(alpha = alpha)
        "event_recommended" -> MaterialTheme.colorScheme.primary.copy(alpha = alpha)
        else -> MaterialTheme.colorScheme.tertiary.copy(alpha = alpha)
    }
}

private fun formatNotificationDate(isoDate: String): String = try {
    val instant = Instant.parse(isoDate)
    val local = instant.atZone(ZoneId.systemDefault())
    DateTimeFormatter.ofPattern("MMM d, HH:mm", Locale.getDefault()).format(local)
} catch (_: Exception) {
    isoDate
}
