package com.bounswe.group9.mobile.ui.eventdetail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bounswe.group9.mobile.data.remote.CommentDto
import com.bounswe.group9.mobile.data.remote.EventDetailDto
import com.bounswe.group9.mobile.data.remote.EventLimitedDto
import com.bounswe.group9.mobile.data.repository.EventDetailResult
import com.bounswe.group9.mobile.data.repository.EventRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class EventDetailUiState(
    val fullDetail: EventDetailDto? = null,
    val limitedPreview: EventLimitedDto? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val actionError: String? = null,
    // Comments
    val comments: List<CommentDto> = emptyList(),
    val commentsLoading: Boolean = false,
    val commentsError: String? = null,
    val commentsTotal: Int = 0,
    val commentsPage: Int = 1,
    val commentsTotalPages: Int = 1,
    val commentText: String = "",
    val commentPosting: Boolean = false
) {
    val isLimited: Boolean get() = limitedPreview != null && fullDetail == null
    val hasData: Boolean get() = fullDetail != null || limitedPreview != null
}

class EventDetailViewModel(
    private val repository: EventRepository = EventRepository()
) : ViewModel() {

    private val _uiState = MutableStateFlow(EventDetailUiState())
    val uiState: StateFlow<EventDetailUiState> = _uiState.asStateFlow()

    private var currentToken: String? = null
    private var currentEventId: String? = null

    fun loadEvent(eventId: String, token: String?) {
        currentToken = token
        currentEventId = eventId
        _uiState.value = EventDetailUiState(isLoading = true)
        viewModelScope.launch {
            repository.getEventDetail(token, eventId).fold(
                onSuccess = { result ->
                    _uiState.value = when (result) {
                        is EventDetailResult.Full -> EventDetailUiState(fullDetail = result.detail)
                        is EventDetailResult.Limited -> EventDetailUiState(limitedPreview = result.preview)
                    }
                    // Load comments for full detail view
                    if (result is EventDetailResult.Full) loadComments(reset = true)
                },
                onFailure = { e ->
                    _uiState.value = EventDetailUiState(errorMessage = e.message)
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
                    _uiState.value = _uiState.value.copy(
                        comments = _uiState.value.comments.filter { it.id != commentId },
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
}
