package com.bounswe.group9.mobile.ui.notifications

import com.bounswe.group9.mobile.data.remote.NotificationDto

data class NotificationUiState(
    val notifications: List<NotificationDto> = emptyList(),
    val unreadCount: Int = 0,
    val isLoading: Boolean = false,
    val isLoadingMore: Boolean = false,
    val errorMessage: String? = null,
    val currentPage: Int = 1,
    val totalPages: Int = 1,
    val isMarkingAllRead: Boolean = false
)
