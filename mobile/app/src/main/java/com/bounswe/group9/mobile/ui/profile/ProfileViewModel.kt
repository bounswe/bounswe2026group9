package com.bounswe.group9.mobile.ui.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bounswe.group9.mobile.data.remote.ProfileUpdateRequestDto
import com.bounswe.group9.mobile.data.repository.ProfileRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ProfileViewModel(
    private val repository: ProfileRepository = ProfileRepository()
) : ViewModel() {

    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()

    private var currentToken: String? = null
    private var currentUserId: String? = null

    fun setToken(token: String?) {
        setCredentials(token, currentUserId)
    }

    fun setCredentials(token: String?, userId: String?) {
        val tokenChanged = currentToken != token
        val userChanged = currentUserId != userId
        if (!tokenChanged && !userChanged) return

        currentToken = token
        currentUserId = userId

        if (token != null && userId != null) {
            loadCurrentProfile()
            loadHostedEvents()
            loadBookmarks(page = 1, reset = true)
        } else {
            _uiState.value = ProfileUiState()
        }
    }

    // ── Load Current User (pre-fill form) ────────────────────────────────────

    private fun loadCurrentProfile() {
        val token = currentToken ?: return
        viewModelScope.launch {
            repository.getMe(token).onSuccess { profile ->
                _uiState.value = _uiState.value.copy(
                    editPhoneNumber = profile.phone_number ?: "",
                    editDateOfBirth = profile.date_of_birth ?: "",
                    editEmailVisibility = profile.email_visibility,
                    editPhoneVisibility = profile.phone_visibility
                )
            }
        }
    }

    // ── Hosted Events ─────────────────────────────────────────────────────────

    fun loadHostedEvents() {
        val token = currentToken ?: return
        val userId = currentUserId ?: return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoadingHostedEvents = true)
            repository.getHostProfile(token, userId).fold(
                onSuccess = { profile ->
                    val now = System.currentTimeMillis()
                    val upcomingCount = profile.hosted_events.count { event ->
                        (event.status == "published" || event.status == "updated") &&
                            try {
                                // Parse the full RFC 3339 / ISO 8601 string, including the
                                // timezone offset, so the comparison with the current instant
                                // is correct for all users regardless of their local timezone.
                                val sdf = java.text.SimpleDateFormat(
                                    "yyyy-MM-dd'T'HH:mm:ssXXX",
                                    java.util.Locale.US
                                )
                                val startMs = sdf.parse(event.start_datetime)?.time ?: 0L
                                startMs > now
                            } catch (_: Exception) { false }
                    }
                    _uiState.value = _uiState.value.copy(
                        hostedEvents = profile.hosted_events,
                        hostedEventsCount = profile.hosted_events_count,
                        averageRating = profile.average_rating,
                        upcomingEventsCount = upcomingCount,
                        isLoadingHostedEvents = false
                    )
                },
                onFailure = {
                    _uiState.value = _uiState.value.copy(isLoadingHostedEvents = false)
                }
            )
        }
    }

    // ── Edit Form ─────────────────────────────────────────────────────────────

    fun onPhoneChange(v: String) {
        _uiState.value = _uiState.value.copy(editPhoneNumber = v)
    }

    fun onDateOfBirthChange(v: String) {
        _uiState.value = _uiState.value.copy(editDateOfBirth = v)
    }

    fun onEmailVisibilityChange(v: Boolean) {
        _uiState.value = _uiState.value.copy(editEmailVisibility = v)
    }

    fun onPhoneVisibilityChange(v: Boolean) {
        _uiState.value = _uiState.value.copy(editPhoneVisibility = v)
    }

    fun saveProfile() {
        val token = currentToken ?: return
        val state = _uiState.value
        val request = ProfileUpdateRequestDto(
            phone_number = state.editPhoneNumber.ifBlank { null },
            date_of_birth = state.editDateOfBirth.ifBlank { null },
            email_visibility = if (state.editEmailVisibility) "public" else "private",
            phone_visibility = if (state.editPhoneVisibility) "public" else "private"
        )
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isSaving = true,
                errorMessage = null,
                successMessage = null
            )
            repository.updateProfile(token, request).fold(
                onSuccess = { profile ->
                    _uiState.value = _uiState.value.copy(
                        editPhoneNumber = profile.phone_number ?: "",
                        editDateOfBirth = profile.date_of_birth ?: "",
                        editEmailVisibility = profile.email_visibility,
                        editPhoneVisibility = profile.phone_visibility,
                        isSaving = false,
                        successMessage = "Profile updated successfully"
                    )
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(
                        isSaving = false,
                        errorMessage = e.message ?: "Failed to update profile"
                    )
                }
            )
        }
    }

    // ── Bookmarks ─────────────────────────────────────────────────────────────

    fun loadBookmarks(page: Int = 1, reset: Boolean = false) {
        val token = currentToken ?: return
        viewModelScope.launch {
            if (reset) {
                _uiState.value = _uiState.value.copy(isLoadingBookmarks = true)
            } else {
                _uiState.value = _uiState.value.copy(isLoadingMoreBookmarks = true)
            }
            repository.getBookmarks(token, page).fold(
                onSuccess = { response ->
                    val items = if (reset) response.items
                                else _uiState.value.bookmarks + response.items
                    _uiState.value = _uiState.value.copy(
                        bookmarks = items,
                        bookmarkPage = response.page,
                        bookmarkTotalPages = response.total_pages,
                        isLoadingBookmarks = false,
                        isLoadingMoreBookmarks = false
                    )
                },
                onFailure = {
                    _uiState.value = _uiState.value.copy(
                        isLoadingBookmarks = false,
                        isLoadingMoreBookmarks = false
                    )
                }
            )
        }
    }

    fun loadNextBookmarkPage() {
        val state = _uiState.value
        if (state.isLoadingMoreBookmarks || state.bookmarkPage >= state.bookmarkTotalPages) return
        loadBookmarks(page = state.bookmarkPage + 1, reset = false)
    }

    fun refresh() {
        if (currentToken == null || currentUserId == null) return
        loadHostedEvents()
        loadBookmarks(page = 1, reset = true)
    }

    fun dismissSuccess() {
        _uiState.value = _uiState.value.copy(successMessage = null)
    }

    fun dismissError() {
        _uiState.value = _uiState.value.copy(errorMessage = null)
    }
}
