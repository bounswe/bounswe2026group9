package com.bounswe.group9.mobile.ui.notifications

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bounswe.group9.mobile.data.repository.NotificationRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class NotificationViewModel(
    private val repository: NotificationRepository = NotificationRepository()
) : ViewModel() {

    private val _uiState = MutableStateFlow(NotificationUiState())
    val uiState: StateFlow<NotificationUiState> = _uiState.asStateFlow()

    private var currentToken: String? = null

    fun setToken(token: String?) {
        if (currentToken == token) return
        currentToken = token
        if (token != null) {
            loadNotifications(page = 1, reset = true)
        } else {
            _uiState.value = NotificationUiState()
        }
    }

    fun loadNotifications(page: Int = 1, reset: Boolean = false) {
        val token = currentToken ?: return
        viewModelScope.launch {
            if (reset) {
                _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            } else {
                _uiState.value = _uiState.value.copy(isLoadingMore = true)
            }

            repository.getNotifications(token, page).fold(
                onSuccess = { response ->
                    val newItems = if (reset) response.items
                                  else _uiState.value.notifications + response.items
                    // Derive unread count: prefer server field, fall back to counting items
                    val unread = if (response.unread_count > 0) response.unread_count
                                 else newItems.count { !it.is_read }
                    _uiState.value = _uiState.value.copy(
                        notifications = newItems,
                        unreadCount = unread,
                        currentPage = response.page,
                        totalPages = response.total_pages,
                        isLoading = false,
                        isLoadingMore = false,
                        errorMessage = null
                    )
                },
                onFailure = { error ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isLoadingMore = false,
                        errorMessage = error.message ?: "Failed to load notifications"
                    )
                }
            )
        }
    }

    fun loadNextPage() {
        val state = _uiState.value
        if (state.isLoadingMore || state.currentPage >= state.totalPages) return
        loadNotifications(page = state.currentPage + 1, reset = false)
    }

    fun markAsRead(notificationId: String) {
        val token = currentToken ?: return
        viewModelScope.launch {
            repository.markAsRead(token, notificationId).onSuccess {
                _uiState.value = _uiState.value.copy(
                    notifications = _uiState.value.notifications.map { n ->
                        if (n.id == notificationId) n.copy(is_read = true) else n
                    },
                    unreadCount = maxOf(0, _uiState.value.unreadCount - 1)
                )
            }
        }
    }

    fun markAllAsRead() {
        val token = currentToken ?: return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isMarkingAllRead = true)
            repository.markAllAsRead(token).fold(
                onSuccess = {
                    _uiState.value = _uiState.value.copy(
                        notifications = _uiState.value.notifications.map { it.copy(is_read = true) },
                        unreadCount = 0,
                        isMarkingAllRead = false
                    )
                },
                onFailure = {
                    _uiState.value = _uiState.value.copy(isMarkingAllRead = false)
                }
            )
        }
    }

    fun refresh() = loadNotifications(page = 1, reset = true)
}
