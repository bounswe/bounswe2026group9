package com.bounswe.group9.mobile.ui.hostprofile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bounswe.group9.mobile.data.remote.HostProfileDto
import com.bounswe.group9.mobile.data.remote.ReviewListItemDto
import com.bounswe.group9.mobile.data.repository.ProfileRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class HostProfileUiState(
    val profile: HostProfileDto? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val ratingScore: Double = 3.0,
    val reviewText: String = "",
    val ratingSubmitting: Boolean = false,
    val ratingSuccess: Boolean = false,
    val actionError: String? = null,
    val reviews: List<ReviewListItemDto> = emptyList(),
    val reviewsTotal: Int = 0,
    val reviewsPage: Int = 1,
    val reviewsTotalPages: Int = 1,
    val reviewsLoading: Boolean = false,
    val reviewsError: String? = null
)

class HostProfileViewModel(
    private val repository: ProfileRepository = ProfileRepository()
) : ViewModel() {

    private val _uiState = MutableStateFlow(HostProfileUiState())
    val uiState: StateFlow<HostProfileUiState> = _uiState.asStateFlow()

    private var currentToken: String? = null
    private var currentHostId: String? = null

    fun loadProfile(userId: String, token: String?) {
        currentToken = token
        currentHostId = userId
        _uiState.value = HostProfileUiState(isLoading = true)
        viewModelScope.launch {
            repository.getHostProfile(token, userId).fold(
                onSuccess = { profile ->
                    _uiState.value = HostProfileUiState(profile = profile)
                    loadReviews(userId, page = 1)
                },
                onFailure = { e ->
                    _uiState.value = HostProfileUiState(errorMessage = e.message)
                }
            )
        }
    }

    fun loadReviews(hostId: String, page: Int = 1) {
        _uiState.value = _uiState.value.copy(reviewsLoading = true, reviewsError = null)
        viewModelScope.launch {
            repository.listHostReviews(hostId, page = page).fold(
                onSuccess = { resp ->
                    val accumulated = if (page == 1) resp.items else _uiState.value.reviews + resp.items
                    _uiState.value = _uiState.value.copy(
                        reviews = accumulated,
                        reviewsTotal = resp.total,
                        reviewsPage = resp.page,
                        reviewsTotalPages = resp.total_pages,
                        reviewsLoading = false
                    )
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(
                        reviewsLoading = false,
                        reviewsError = e.message
                    )
                }
            )
        }
    }

    fun loadNextReviewsPage() {
        val state = _uiState.value
        val hostId = currentHostId ?: return
        if (state.reviewsLoading || state.reviewsPage >= state.reviewsTotalPages) return
        loadReviews(hostId, page = state.reviewsPage + 1)
    }

    fun onRatingChange(score: Double) {
        _uiState.value = _uiState.value.copy(ratingScore = score)
    }

    fun onReviewTextChange(text: String) {
        if (text.length <= 1000) _uiState.value = _uiState.value.copy(reviewText = text)
    }

    fun submitRating(hostId: String) {
        val token = currentToken ?: return
        val state = _uiState.value
        _uiState.value = state.copy(ratingSubmitting = true, actionError = null)
        viewModelScope.launch {
            repository.rateHost(token, hostId, state.ratingScore, state.reviewText.ifBlank { null }).fold(
                onSuccess = {
                    _uiState.value = _uiState.value.copy(
                        ratingSubmitting = false,
                        ratingSuccess = true,
                        reviewText = ""
                    )
                    delay(800)
                    loadProfile(hostId, currentToken)
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
