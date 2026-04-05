package com.bounswe.group9.mobile.data.repository

import com.bounswe.group9.mobile.data.remote.NotificationListResponseDto
import com.bounswe.group9.mobile.data.remote.NotificationReadAllResponseDto
import com.bounswe.group9.mobile.data.remote.NotificationReadResponseDto
import com.bounswe.group9.mobile.data.remote.RetrofitProvider

class NotificationRepository {

    suspend fun getNotifications(
        token: String,
        page: Int = 1,
        pageSize: Int = 20
    ): Result<NotificationListResponseDto> = runCatching {
        RetrofitProvider.apiService.getNotifications(
            token = "Bearer $token",
            page = page,
            pageSize = pageSize
        )
    }

    suspend fun markAsRead(
        token: String,
        notificationId: String
    ): Result<NotificationReadResponseDto> = runCatching {
        RetrofitProvider.apiService.markNotificationRead(
            notificationId = notificationId,
            token = "Bearer $token"
        )
    }

    suspend fun markAllAsRead(token: String): Result<NotificationReadAllResponseDto> = runCatching {
        RetrofitProvider.apiService.markAllNotificationsRead(token = "Bearer $token")
    }
}
