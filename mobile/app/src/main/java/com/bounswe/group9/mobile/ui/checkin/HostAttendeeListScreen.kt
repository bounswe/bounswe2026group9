package com.bounswe.group9.mobile.ui.checkin

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.bounswe.group9.mobile.data.remote.AttendeeStatusDto
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HostAttendeeListScreen(
    eventId: String,
    authToken: String?,
    onBack: () -> Unit,
    onNavigateToProfile: (String) -> Unit = {},
    viewModel: HostAttendeeListViewModel = remember { HostAttendeeListViewModel() }
) {
    val state by viewModel.uiState.collectAsState()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(eventId, authToken) {
        if (authToken != null) viewModel.load(authToken, eventId)
    }

    LaunchedEffect(state.toast) {
        state.toast?.let {
            snackbar.showSnackbar(it)
            viewModel.consumeToast()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    val total = state.attendees.size
                    val checked = state.checkedInCount
                    Text(if (total > 0) "Attendees ($checked / $total)" else "Attendees")
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(
                        onClick = {
                            if (authToken != null) viewModel.refresh(authToken, eventId)
                        },
                        enabled = !state.isLoading
                    ) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                    }
                }
            )
        },
        snackbarHost = { SnackbarHost(snackbar) }
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when {
                authToken == null -> CenteredMessage("Sign in to view attendees")
                state.isLoading && state.attendees.isEmpty() -> Box(
                    Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) { CircularProgressIndicator() }
                state.errorMessage != null && state.attendees.isEmpty() ->
                    CenteredMessage(state.errorMessage!!)
                state.attendees.isEmpty() ->
                    CenteredMessage("No one has marked Going yet.")
                else -> {
                    // authToken non-null in this branch (the null case is matched above).
                    val token = authToken!!
                    LazyColumn(
                        contentPadding = PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.fillMaxSize()
                    ) {
                        items(state.attendees, key = { it.user_id }) { attendee ->
                            AttendeeRow(
                                attendee = attendee,
                                isMarking = attendee.user_id in state.markingIds,
                                onMarkIn = { viewModel.markIn(token, eventId, attendee.user_id) },
                                onProfileClick = { onNavigateToProfile(attendee.user_id) }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun AttendeeRow(
    attendee: AttendeeStatusDto,
    isMarking: Boolean,
    onMarkIn: () -> Unit,
    onProfileClick: () -> Unit
) {
    val isCheckedIn = attendee.checked_in_at != null
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isCheckedIn)
                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
            else MaterialTheme.colorScheme.surface
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    text = "@${attendee.username}",
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier
                )
                Spacer(Modifier.height(2.dp))
                if (isCheckedIn) {
                    Text(
                        "Checked in · ${formatCheckInTime(attendee.checked_in_at!!)}",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    Text(
                        "Pending",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            if (isCheckedIn) {
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Color(0xFF16A34A).copy(alpha = 0.15f)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            Icons.Default.Check,
                            contentDescription = null,
                            tint = Color(0xFF16A34A),
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(Modifier.width(4.dp))
                        Text("In", color = Color(0xFF16A34A), fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                    }
                }
            } else {
                OutlinedButton(
                    onClick = onMarkIn,
                    enabled = !isMarking
                ) {
                    if (isMarking) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            strokeWidth = 2.dp
                        )
                        Spacer(Modifier.width(6.dp))
                    }
                    Text("Mark in", fontSize = 12.sp)
                }
            }
        }
    }
}

@Composable
private fun CenteredMessage(text: String) {
    Box(Modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.Center) {
        Text(text, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

private fun formatCheckInTime(iso: String): String {
    return try {
        val parser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
        val display = SimpleDateFormat("MMM d, HH:mm", Locale.getDefault())
        display.timeZone = TimeZone.getDefault()
        val date = parser.parse(iso)
        if (date != null) display.format(date) else iso
    } catch (_: Exception) { iso }
}
