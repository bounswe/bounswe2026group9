package com.bounswe.group9.mobile.data.repository

import android.util.Log
import com.bounswe.group9.mobile.data.remote.CategoryDto
import com.bounswe.group9.mobile.data.remote.EventListItemDto
import com.bounswe.group9.mobile.data.remote.EventListResponse
import com.bounswe.group9.mobile.data.remote.RetrofitProvider

class EventRepository {

    suspend fun getEvents(
        token: String? = null,
        search: String? = null,
        categoryId: String? = null,
        temporalFilter: String? = null,
        page: Int = 1,
        pageSize: Int = 20
    ): Result<EventListResponse> {
        return try {
            val authHeader = token?.let { "Bearer $it" }
            val response = RetrofitProvider.apiService.getEvents(
                token = authHeader,
                search = search?.takeIf { it.isNotBlank() },
                categoryId = categoryId,
                temporalFilter = temporalFilter,
                page = page,
                pageSize = pageSize
            )
            Result.success(response)
        } catch (e: retrofit2.HttpException) {
            // If token expired (401), retry without token — discovery is public
            if (e.code() == 401 && token != null) {
                Log.w("EventRepository", "Token rejected (401), retrying without auth")
                return getEvents(null, search, categoryId, temporalFilter, page, pageSize)
            }
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("EventRepository", "getEvents HTTP ${e.code()}: $body")
            Result.failure(Exception("${e.code()}: $body"))
        } catch (e: Exception) {
            Log.e("EventRepository", "getEvents failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun getCategories(): Result<List<CategoryDto>> {
        return try {
            val cats = RetrofitProvider.apiService.getCategories()
            Result.success(cats)
        } catch (e: Exception) {
            Log.e("EventRepository", "getCategories failed: ${e.message}", e)
            Result.failure(e)
        }
    }
}
