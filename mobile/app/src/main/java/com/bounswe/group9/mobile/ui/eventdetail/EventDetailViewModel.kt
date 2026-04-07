package com.bounswe.group9.mobile.ui.eventdetail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bounswe.group9.mobile.data.remote.AccessRequestResponseDto
import com.bounswe.group9.mobile.data.remote.CommentDto
import com.bounswe.group9.mobile.data.remote.EventDetailDto
import com.bounswe.group9.mobile.data.remote.EventLimitedDto
import com.bounswe.group9.mobile.data.remote.InviteResponseDto
import com.bounswe.group9.mobile.data.repository.EventDetailError
import com.bounswe.group9.mobile.data.repository.EventDetailResult
import com.bounswe.group9.mobile.data.repository.EventRepository
import com.bounswe.group9.mobile.data.repository.ProfileRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class EventDetailUiState(
    val fullDetail: EventDetailDto? = null,
    val limitedPreview: EventLimitedDto? = null,
    val hostUsername: String? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val detailError: EventDetailError? = null,
    val actionError: String? = null,
    // DOB verification
    val dobInput: String = "",
    val dobSubmitting: Boolean = false,
    // Access request
    val accessRequesting: Boolean = false,
    val accessRequestSent: Boolean = false,
    // Comments
    val comments: List<CommentDto> = emptyList(),
    val commentsLoading: Boolean = false,
    val commentsError: String? = null,
    val commentsTotal: Int = 0,
    val commentsPage: Int = 1,
    val commentsTotalPages: Int = 1,
    val commentText: String = "",
    val commentPosting: Boolean = false,
    // Access request (non-host)
    val accessRequestStatus: String? = null,  // null | "pending" | "approved" | "rejected"
    val isRequestingAccess: Boolean = false,
    // Host action loading (cancel / delete / publish)
    val isHostActionLoading: Boolean = false,
    // Invite & access request management (host)
    val invites: List<InviteResponseDto> = emptyList(),
    val accessRequests: List<AccessRequestResponseDto> = emptyList(),
    val isLoadingInviteSection: Boolean = false,
    val isCreatingInvite: Boolean = false,
    val inviteSectionError: String? = null
) {
    val isLimited: Boolean get() = limitedPreview != null && fullDetail == null
    val hasData: Boolean get() = fullDetail != null || limitedPreview != null
}

class EventDetailViewModel(
    private val repository: EventRepository = EventRepository(),
    private val profileRepository: ProfileRepository = ProfileRepository()
) : ViewModel() {

    private val _uiState = MutableStateFlow(EventDetailUiState())
    val uiState: StateFlow<EventDetailUiState> = _uiState.asStateFlow()

    private var currentToken: String? = null
    private var currentEventId: String? = null

    companion object {
        // Session-level cache: eventId -> accessRequestStatus
        // Persists across ViewModel recreations while the app is alive
        private val accessRequestCache = mutableMapOf<String, String>()
    }

    fun loadEvent(eventId: String, token: String?) {
        currentToken = token
        currentEventId = eventId
        _uiState.value = EventDetailUiState(isLoading = true)
        viewModelScope.launch {
            val result = repository.getEventDetail(token, eventId)
            if (result.isSuccess) {
                when (val r = result.getOrNull()!!) {
                    is EventDetailResult.Full -> {
                        _uiState.value = EventDetailUiState(fullDetail = r.detail)
                        loadComments(reset = true)
                        if (token != null) loadInviteSection()
                        loadHostUsername(r.detail.host_id)
                    }
                    is EventDetailResult.Limited -> {
                        // Age-restricted limited preview: check user age before showing
                        if (r.preview.is_age_restricted && token != null) {
                            val ageError = checkAgeRestriction(token)
                            if (ageError != null) {
                                _uiState.value = EventDetailUiState(
                                    detailError = ageError,
                                    errorMessage = ageError.message
                                )
                                return@launch
                            }
                        }
                        // Server provides access_request_status authoritatively — seed cache and use directly
                        val serverStatus = r.preview.access_request_status
                        if (serverStatus != null) {
                            accessRequestCache[eventId] = serverStatus
                        }
                        _uiState.value = EventDetailUiState(
                            limitedPreview = r.preview,
                            accessRequestStatus = serverStatus ?: accessRequestCache[eventId]
                        )
                        // If server already says approved, reload for full detail
                        if (serverStatus == "approved") {
                            loadEvent(eventId, token)
                        }
                    }
                }
            } else {
                val e = result.exceptionOrNull()!!
                val typedError = e as? EventDetailError
                _uiState.value = EventDetailUiState(
                    errorMessage = e.message,
                    detailError = typedError
                )
            }
        }
    }

    // ── DOB Verification ──

    fun onDobChange(dob: String) {
        _uiState.value = _uiState.value.copy(dobInput = dob)
    }

    fun submitDob() {
        val token = currentToken ?: return
        val dob = _uiState.value.dobInput.trim()
        if (dob.isEmpty()) return

        _uiState.value = _uiState.value.copy(dobSubmitting = true, actionError = null)
        viewModelScope.launch {
            repository.updateDateOfBirth(token, dob).fold(
                onSuccess = {
                    // DOB saved — reload event detail (backend will now allow or deny based on age)
                    _uiState.value = _uiState.value.copy(dobSubmitting = false)
                    currentEventId?.let { loadEvent(it, currentToken) }
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(
                        dobSubmitting = false,
                        actionError = e.message
                    )
                }
            )
        }
    }

    // ── Comments ──

    fun onCommentTextChange(text: String) {
        _uiState.value = _uiState.value.copy(commentText = text)
    }

    fun postComment() {
        val token = currentToken ?: return
        val eventId = currentEventId ?: return
        val text = _uiState.value.commentText.trim()
        if (text.isEmpty()) return

        _uiState.value = _uiState.value.copy(commentPosting = true)
        viewModelScope.launch {
            repository.postComment(token, eventId, text).fold(
                onSuccess = { newComment ->
                    _uiState.value = _uiState.value.copy(
                        comments = listOf(newComment) + _uiState.value.comments,
                        commentsTotal = _uiState.value.commentsTotal + 1,
                        commentText = "",
                        commentPosting = false
                    )
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(
                        commentPosting = false,
                        actionError = e.message
                    )
                }
            )
        }
    }

    fun deleteComment(commentId: String) {
        val token = currentToken ?: return
        val eventId = currentEventId ?: return
        viewModelScope.launch {
            repository.deleteComment(token, eventId, commentId).fold(
                onSuccess = {
                    val updated = _uiState.value.comments
                        .filter { it.id != commentId }
                        .map { it.copy(replies = it.replies.filter { r -> r.id != commentId }) }
                    _uiState.value = _uiState.value.copy(
                        comments = updated,
                        commentsTotal = (_uiState.value.commentsTotal - 1).coerceAtLeast(0)
                    )
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(actionError = e.message)
                }
            )
        }
    }

    fun loadMoreComments() {
        if (_uiState.value.commentsLoading || _uiState.value.commentsPage >= _uiState.value.commentsTotalPages) return
        loadComments(reset = false)
    }

    private fun loadComments(reset: Boolean) {
        val eventId = currentEventId ?: return
        val page = if (reset) 1 else _uiState.value.commentsPage + 1
        _uiState.value = _uiState.value.copy(commentsLoading = true, commentsError = null)
        viewModelScope.launch {
            repository.getComments(eventId, page).fold(
                onSuccess = { response ->
                    val newComments = if (reset) response.items else _uiState.value.comments + response.items
                    _uiState.value = _uiState.value.copy(
                        comments = newComments,
                        commentsTotal = response.total,
                        commentsPage = response.page,
                        commentsTotalPages = response.total_pages,
                        commentsLoading = false,
                        commentsError = null
                    )
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(
                        commentsLoading = false,
                        commentsError = e.message ?: "Failed to load comments"
                    )
                }
            )
        }
    }

    fun clearActionError() {
        _uiState.value = _uiState.value.copy(actionError = null)
    }

    fun toggleBookmark() {
        val detail = _uiState.value.fullDetail ?: return
        val token = currentToken ?: return
        val isCurrentlyBookmarked = detail.is_bookmarked == true

        // Optimistic update
        _uiState.value = _uiState.value.copy(
            fullDetail = detail.copy(is_bookmarked = !isCurrentlyBookmarked),
            actionError = null
        )

        viewModelScope.launch {
            val result = if (isCurrentlyBookmarked) {
                repository.removeBookmark(token, detail.id)
            } else {
                repository.addBookmark(token, detail.id)
            }
            result.onFailure { e ->
                // Rollback on failure
                _uiState.value = _uiState.value.copy(
                    fullDetail = _uiState.value.fullDetail?.copy(is_bookmarked = isCurrentlyBookmarked),
                    actionError = e.message
                )
            }
        }
    }

    fun setGoing() {
        val detail = _uiState.value.fullDetail ?: return
        val token = currentToken ?: return
        if (detail.is_full == true && detail.attendance_status != "going") return

        val oldStatus = detail.attendance_status
        val oldGoingCount = detail.going_count

        // Optimistic update
        val newGoingCount = if (oldStatus != "going") oldGoingCount + 1 else oldGoingCount
        _uiState.value = _uiState.value.copy(
            fullDetail = detail.copy(
                attendance_status = "going",
                going_count = newGoingCount,
                is_full = if (detail.attendee_limit != null) newGoingCount >= detail.attendee_limit else null
            ),
            actionError = null
        )

        viewModelScope.launch {
            repository.setAttendance(token, detail.id, "going").onFailure { e ->
                // Rollback
                _uiState.value = _uiState.value.copy(
                    fullDetail = _uiState.value.fullDetail?.copy(
                        attendance_status = oldStatus,
                        going_count = oldGoingCount,
                        is_full = if (detail.attendee_limit != null) oldGoingCount >= detail.attendee_limit else null
                    ),
                    actionError = e.message
                )
            }
        }
    }

    fun removeAttendance() {
        val detail = _uiState.value.fullDetail ?: return
        val token = currentToken ?: return

        val oldStatus = detail.attendance_status ?: return
        val oldGoingCount = detail.going_count

        // Optimistic update — only going affects count (interested removed from mobile)
        val newGoingCount = if (oldStatus == "going") oldGoingCount - 1 else oldGoingCount
        _uiState.value = _uiState.value.copy(
            fullDetail = detail.copy(
                attendance_status = null,
                going_count = newGoingCount,
                is_full = if (detail.attendee_limit != null) newGoingCount >= detail.attendee_limit else null
            ),
            actionError = null
        )

        viewModelScope.launch {
            repository.removeAttendance(token, detail.id).onFailure { e ->
                _uiState.value = _uiState.value.copy(
                    fullDetail = _uiState.value.fullDetail?.copy(
                        attendance_status = oldStatus,
                        going_count = oldGoingCount,
                        is_full = if (detail.attendee_limit != null) oldGoingCount >= detail.attendee_limit else null
                    ),
                    actionError = e.message
                )
            }
        }
    }

    // ── Invite Section (host) ─────────────────────────────────────────────────

    fun loadInviteSection() {
        val token = currentToken ?: return
        val eventId = currentEventId ?: return
        _uiState.value = _uiState.value.copy(isLoadingInviteSection = true, inviteSectionError = null)
        viewModelScope.launch {
            val invitesResult = repository.listInvites(token, eventId)
            val requestsResult = repository.listAccessRequests(token, eventId)
            _uiState.value = _uiState.value.copy(
                invites = invitesResult.getOrDefault(com.bounswe.group9.mobile.data.remote.InviteListResponseDto(emptyList())).items,
                accessRequests = requestsResult.getOrDefault(com.bounswe.group9.mobile.data.remote.AccessRequestListResponseDto(emptyList())).items
                    .filter { it.status == "pending" },
                isLoadingInviteSection = false,
                inviteSectionError = invitesResult.exceptionOrNull()?.message
                    ?: requestsResult.exceptionOrNull()?.message
            )
        }
    }

    fun createInvite() {
        val token = currentToken ?: return
        val eventId = currentEventId ?: return
        _uiState.value = _uiState.value.copy(isCreatingInvite = true)
        viewModelScope.launch {
            repository.createInvite(token, eventId).fold(
                onSuccess = { invite ->
                    _uiState.value = _uiState.value.copy(
                        invites = listOf(invite) + _uiState.value.invites,
                        isCreatingInvite = false
                    )
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(
                        isCreatingInvite = false,
                        actionError = e.message
                    )
                }
            )
        }
    }

    fun decideRequest(requestId: String, decision: String) {
        val token = currentToken ?: return
        val eventId = currentEventId ?: return
        viewModelScope.launch {
            repository.decideAccessRequest(token, eventId, requestId, decision).fold(
                onSuccess = {
                    // Remove from pending list
                    _uiState.value = _uiState.value.copy(
                        accessRequests = _uiState.value.accessRequests.filter { it.id != requestId }
                    )
                    // If approved → reload event so approved user sees full view next time
                    if (decision == "approved") loadEvent(eventId, token)
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(actionError = e.message)
                }
            )
        }
    }

    // ── Access Request (non-host) ─────────────────────────────────────────────

    fun requestAccess() {
        val token = currentToken ?: return
        val eventId = currentEventId ?: return
        _uiState.value = _uiState.value.copy(isRequestingAccess = true)
        viewModelScope.launch {
            repository.requestAccess(token, eventId).fold(
                onSuccess = { req ->
                    accessRequestCache[eventId] = req.status
                    _uiState.value = _uiState.value.copy(
                        accessRequestStatus = req.status,
                        isRequestingAccess = false
                    )
                },
                onFailure = { e ->
                    val msg = e.message ?: ""
                    when {
                        msg.contains("already exists", ignoreCase = true) -> {
                            accessRequestCache[eventId] = "pending"
                            _uiState.value = _uiState.value.copy(
                                accessRequestStatus = "pending",
                                isRequestingAccess = false
                            )
                        }
                        msg.contains("already granted", ignoreCase = true) -> {
                            accessRequestCache[eventId] = "approved"
                            _uiState.value = _uiState.value.copy(isRequestingAccess = false)
                            loadEvent(eventId, token)
                        }
                        else -> {
                            _uiState.value = _uiState.value.copy(
                                isRequestingAccess = false,
                                actionError = e.message
                            )
                        }
                    }
                }
            )
        }
    }

    // ── Host Actions ──────────────────────────────────────────────────────────

    fun publishEvent(onSuccess: () -> Unit) {
        val token = currentToken ?: return
        val eventId = currentEventId ?: return
        _uiState.value = _uiState.value.copy(isHostActionLoading = true, actionError = null)
        viewModelScope.launch {
            repository.changeEventStatus(token, eventId, "published").fold(
                onSuccess = { updated ->
                    _uiState.value = _uiState.value.copy(
                        fullDetail = updated,
                        isHostActionLoading = false
                    )
                    onSuccess()
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(
                        isHostActionLoading = false,
                        actionError = e.message
                    )
                }
            )
        }
    }

    fun cancelEvent(onSuccess: () -> Unit) {
        val token = currentToken ?: return
        val eventId = currentEventId ?: return
        _uiState.value = _uiState.value.copy(isHostActionLoading = true, actionError = null)
        viewModelScope.launch {
            repository.changeEventStatus(token, eventId, "cancelled").fold(
                onSuccess = { updated ->
                    _uiState.value = _uiState.value.copy(
                        fullDetail = updated,
                        isHostActionLoading = false
                    )
                    onSuccess()
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(
                        isHostActionLoading = false,
                        actionError = e.message
                    )
                }
            )
        }
    }

    fun deleteEvent(onSuccess: () -> Unit) {
        val token = currentToken ?: return
        val eventId = currentEventId ?: return
        _uiState.value = _uiState.value.copy(isHostActionLoading = true, actionError = null)
        viewModelScope.launch {
            repository.deleteEvent(token, eventId).fold(
                onSuccess = {
                    _uiState.value = _uiState.value.copy(isHostActionLoading = false)
                    onSuccess()
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(
                        isHostActionLoading = false,
                        actionError = e.message
                    )
                }
            )
        }
    }

    private fun loadHostUsername(hostId: String) {
        viewModelScope.launch {
            profileRepository.getHostProfile(null, hostId).onSuccess { profile ->
                _uiState.value = _uiState.value.copy(hostUsername = profile.username)
            }
        }
    }

    /**
     * Returns an [EventDetailError] if [token] user is blocked by age restriction, null if allowed.
     * Fetches /me to get DOB; if no DOB returns [EventDetailError.DobRequired],
     * if under 18 returns [EventDetailError.Underage].
     */
    private suspend fun checkAgeRestriction(token: String): EventDetailError? {
        val profile = profileRepository.getMe(token).getOrNull() ?: return null
        val dob = profile.date_of_birth
        if (dob.isNullOrBlank()) return EventDetailError.DobRequired()
        return if (isUnder18(dob)) EventDetailError.Underage() else null
    }

    private fun isUnder18(dob: String): Boolean {
        return try {
            val sdf = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.US)
            val dobDate = sdf.parse(dob) ?: return false
            val cal = java.util.Calendar.getInstance()
            val today = cal.time
            cal.time = dobDate
            val dobYear = cal.get(java.util.Calendar.YEAR)
            val dobMonth = cal.get(java.util.Calendar.MONTH)
            val dobDay = cal.get(java.util.Calendar.DAY_OF_MONTH)
            cal.time = today
            val todayYear = cal.get(java.util.Calendar.YEAR)
            val todayMonth = cal.get(java.util.Calendar.MONTH)
            val todayDay = cal.get(java.util.Calendar.DAY_OF_MONTH)
            val age = todayYear - dobYear -
                if (todayMonth < dobMonth || (todayMonth == dobMonth && todayDay < dobDay)) 1 else 0
            age < 18
        } catch (_: Exception) { false }
    }

    /** On limited view load — only restore status from session cache. No auto-request creation. */
    private fun checkAccessRequestStatus() {
        val eventId = currentEventId ?: return
        val cached = accessRequestCache[eventId]
        if (cached != null) {
            _uiState.value = _uiState.value.copy(accessRequestStatus = cached)
            if (cached == "approved") {
                loadEvent(eventId, currentToken)
            }
        }
        // If no cache → show "Request Access" button (status = null). User must explicitly click.
    }
}
