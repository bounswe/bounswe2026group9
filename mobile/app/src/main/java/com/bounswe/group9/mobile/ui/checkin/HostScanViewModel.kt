package com.bounswe.group9.mobile.ui.checkin

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bounswe.group9.mobile.data.repository.CheckInOutcome
import com.bounswe.group9.mobile.data.repository.CheckInRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** Visual state shown over the camera preview. */
sealed class ScanState {
    object Idle : ScanState()
    object Submitting : ScanState()
    data class Success(val username: String?, val checkedInAt: String) : ScanState()
    data class Error(val message: String) : ScanState()
}

data class HostScanUiState(
    val scanState: ScanState = ScanState.Idle,
    val totalCheckIns: Int = 0,
    val lastSubmittedToken: String? = null
)

/**
 * Drives the host's scan screen. The screen feeds raw decoded QR strings via [submit];
 * the VM debounces by token, calls the backend, and exposes a state for UI feedback.
 */
class HostScanViewModel(
    private val repository: CheckInRepository = CheckInRepository()
) : ViewModel() {

    private val _uiState = MutableStateFlow(HostScanUiState())
    val uiState: StateFlow<HostScanUiState> = _uiState.asStateFlow()

    /** Already-submitted tokens — prevents repeating network calls when the camera re-decodes. */
    private val submittedTokens = mutableSetOf<String>()

    fun submit(token: String, eventId: String, authToken: String) {
        if (token.isBlank()) return
        if (token in submittedTokens) return
        if (_uiState.value.scanState is ScanState.Submitting) return

        submittedTokens.add(token)
        _uiState.value = _uiState.value.copy(
            scanState = ScanState.Submitting,
            lastSubmittedToken = token
        )

        viewModelScope.launch {
            val outcome = repository.submitCheckIn(authToken, eventId, token)
            val newState: ScanState = when (outcome) {
                is CheckInOutcome.Success -> ScanState.Success(
                    username = outcome.result.username,
                    checkedInAt = outcome.result.checked_in_at
                )
                CheckInOutcome.InvalidPayload -> ScanState.Error("Invalid QR code")
                CheckInOutcome.NotHost -> ScanState.Error("You are not the host of this event")
                CheckInOutcome.NotGoing -> ScanState.Error("This person isn't on the Going list")
                CheckInOutcome.AlreadyCheckedIn -> ScanState.Error("Already checked in")
                is CheckInOutcome.Error -> ScanState.Error(outcome.message)
            }
            val incrementCount = outcome is CheckInOutcome.Success
            _uiState.value = _uiState.value.copy(
                scanState = newState,
                totalCheckIns = if (incrementCount) _uiState.value.totalCheckIns + 1
                                else _uiState.value.totalCheckIns
            )
        }
    }

    /** UI calls this after showing the result for ~1.5s — back to scanning. */
    fun acknowledge() {
        _uiState.value = _uiState.value.copy(scanState = ScanState.Idle)
    }
}
