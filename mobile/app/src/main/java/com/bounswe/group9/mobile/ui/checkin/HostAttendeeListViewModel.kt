package com.bounswe.group9.mobile.ui.checkin

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bounswe.group9.mobile.data.remote.AttendeeStatusDto
import com.bounswe.group9.mobile.data.repository.CheckInOutcome
import com.bounswe.group9.mobile.data.repository.CheckInRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class HostAttendeeListUiState(
    val attendees: List<AttendeeStatusDto> = emptyList(),
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    /** user_ids currently being marked-in via the manual fallback. */
    val markingIds: Set<String> = emptySet(),
    val toast: String? = null
) {
    val checkedInCount: Int get() = attendees.count { it.checked_in_at != null }
}

/**
 * Backs the host's attendee roster screen. Pull-to-refresh via [refresh],
 * manual check-in via [markIn], local optimistic update on success.
 */
class HostAttendeeListViewModel(
    private val repository: CheckInRepository = CheckInRepository()
) : ViewModel() {

    private val _uiState = MutableStateFlow(HostAttendeeListUiState())
    val uiState: StateFlow<HostAttendeeListUiState> = _uiState.asStateFlow()

    fun load(token: String, eventId: String) {
        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
        viewModelScope.launch {
            repository.listAttendees(token, eventId).fold(
                onSuccess = { items ->
                    _uiState.value = _uiState.value.copy(
                        attendees = items,
                        isLoading = false
                    )
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = e.message ?: "Failed to load attendees"
                    )
                }
            )
        }
    }

    fun refresh(token: String, eventId: String) = load(token, eventId)

    fun markIn(token: String, eventId: String, userId: String) {
        if (userId in _uiState.value.markingIds) return
        _uiState.value = _uiState.value.copy(markingIds = _uiState.value.markingIds + userId)
        viewModelScope.launch {
            val outcome = repository.manualCheckIn(token, eventId, userId)
            val (newAttendees, toast) = when (outcome) {
                is CheckInOutcome.Success -> {
                    val updated = _uiState.value.attendees.map {
                        if (it.user_id == userId) it.copy(checked_in_at = outcome.result.checked_in_at) else it
                    }
                    updated to "Marked in"
                }
                CheckInOutcome.AlreadyCheckedIn -> _uiState.value.attendees to "Already checked in"
                CheckInOutcome.NotGoing -> _uiState.value.attendees to "Attendee is not going"
                CheckInOutcome.NotHost -> _uiState.value.attendees to "Not authorised"
                CheckInOutcome.InvalidPayload -> _uiState.value.attendees to "Invalid request"
                is CheckInOutcome.Error -> _uiState.value.attendees to outcome.message
            }
            _uiState.value = _uiState.value.copy(
                attendees = newAttendees,
                markingIds = _uiState.value.markingIds - userId,
                toast = toast
            )
        }
    }

    fun consumeToast() {
        _uiState.value = _uiState.value.copy(toast = null)
    }
}
