package com.bounswe.group9.mobile.ui.eventdetail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
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
    val actionError: String? = null
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
                },
                onFailure = { e ->
                    _uiState.value = EventDetailUiState(errorMessage = e.message)
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
