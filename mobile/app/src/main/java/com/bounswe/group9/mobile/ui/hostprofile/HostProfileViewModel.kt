package com.bounswe.group9.mobile.ui.hostprofile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bounswe.group9.mobile.data.remote.EventListItemDto
import com.bounswe.group9.mobile.data.remote.HostProfileDto
import com.bounswe.group9.mobile.data.repository.ProfileRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class HostProfileUiState(
    val profile: HostProfileDto? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val ratingScore: Double = 3.0,
    val ratingSubmitting: Boolean = false,
    val ratingSuccess: Boolean = false,
    val actionError: String? = null
)

class HostProfileViewModel(
    private val repository: ProfileRepository = ProfileRepository()
) : ViewModel() {

    private val _uiState = MutableStateFlow(HostProfileUiState())
    val uiState: StateFlow<HostProfileUiState> = _uiState.asStateFlow()

    private var currentToken: String? = null

    fun loadProfile(userId: String, token: String?) {
        currentToken = token
        _uiState.value = HostProfileUiState(isLoading = true)
        viewModelScope.launch {
            repository.getHostProfile(token, userId).fold(
                onSuccess = { profile ->
                    _uiState.value = HostProfileUiState(profile = profile)
                },
                onFailure = { e ->
                    _uiState.value = HostProfileUiState(errorMessage = e.message)
                }
            )
        }
    }

    fun onRatingChange(score: Double) {
        _uiState.value = _uiState.value.copy(ratingScore = score)
    }

    fun submitRating(hostId: String) {
        val token = currentToken ?: return
        _uiState.value = _uiState.value.copy(ratingSubmitting = true, actionError = null)
        viewModelScope.launch {
            repository.rateHost(token, hostId, _uiState.value.ratingScore).fold(
                onSuccess = {
                    _uiState.value = _uiState.value.copy(
                        ratingSubmitting = false,
                        ratingSuccess = true
                    )
                    // Reload profile to get updated average
                    _uiState.value.profile?.let { loadProfile(it.id, currentToken) }
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(
                        ratingSubmitting = false,
                        actionError = e.message
                    )
                }
            )
        }
    }

    fun clearActionError() {
        _uiState.value = _uiState.value.copy(actionError = null)
    }
}
