package com.bounswe.group9.mobile.ui.invite

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bounswe.group9.mobile.data.repository.EventRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

// ── ViewModel ──────────────────────────────────────────────────────────────────

data class InviteAcceptUiState(
    val isLoading: Boolean = true,
    val success: Boolean = false,
    val errorMessage: String? = null
)

class InviteAcceptViewModel(
    private val repository: EventRepository = EventRepository()
) : ViewModel() {

    private val _uiState = MutableStateFlow(InviteAcceptUiState())
    val uiState: StateFlow<InviteAcceptUiState> = _uiState.asStateFlow()

    fun acceptInvite(token: String, eventId: String, authToken: String) {
        viewModelScope.launch {
            repository.acceptInvite(authToken, eventId, token).fold(
                onSuccess = {
                    _uiState.value = InviteAcceptUiState(isLoading = false, success = true)
                },
                onFailure = { e ->
                    val msg = e.message ?: "Failed to accept invite"
                    val displayMsg = when {
                        msg.contains("already granted", ignoreCase = true) ->
                            "You already have access to this event!"
                        msg.contains("expired", ignoreCase = true) ->
                            "This invite link has expired."
                        msg.contains("maximum uses", ignoreCase = true) ->
                            "This invite link has reached its usage limit."
                        msg.contains("not found", ignoreCase = true) ->
                            "Invalid invite link."
                        else -> msg
                    }
                    _uiState.value = InviteAcceptUiState(isLoading = false, errorMessage = displayMsg)
                }
            )
        }
    }
}

// ── Screen ─────────────────────────────────────────────────────────────────────

@Composable
fun InviteAcceptScreen(
    viewModel: InviteAcceptViewModel,
    eventId: String,
    inviteToken: String,
    authToken: String?,
    onNavigateToEvent: (String) -> Unit,
    onNavigateHome: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(eventId, inviteToken) {
        if (authToken != null) {
            viewModel.acceptInvite(inviteToken, eventId, authToken)
        } else {
            // Not logged in — redirect to home
            onNavigateHome()
        }
    }

    // Auto-navigate to event after success
    LaunchedEffect(uiState.success) {
        if (uiState.success) {
            kotlinx.coroutines.delay(1500)
            onNavigateToEvent(eventId)
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        contentAlignment = Alignment.Center
    ) {
        when {
            uiState.isLoading -> {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                    Text(
                        "Accepting invite...",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            uiState.success -> {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Icon(
                        Icons.Default.CheckCircle,
                        contentDescription = null,
                        modifier = Modifier.size(72.dp),
                        tint = MaterialTheme.colorScheme.primary
                    )
                    Text(
                        "Access Granted!",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        "You now have access to this event.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center
                    )
                    Text(
                        "Taking you to the event...",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            uiState.errorMessage != null -> {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Icon(
                        Icons.Default.ErrorOutline,
                        contentDescription = null,
                        modifier = Modifier.size(64.dp),
                        tint = MaterialTheme.colorScheme.error
                    )
                    Text(
                        "Invite Error",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        uiState.errorMessage!!,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center
                    )
                    Spacer(Modifier.height(8.dp))
                    // If already has access → go to event anyway
                    if (uiState.errorMessage!!.contains("already", ignoreCase = true)) {
                        Button(onClick = { onNavigateToEvent(eventId) }) {
                            Text("Go to Event")
                        }
                    } else {
                        OutlinedButton(onClick = onNavigateHome) {
                            Text("Back to Home")
                        }
                    }
                }
            }
        }
    }
}
