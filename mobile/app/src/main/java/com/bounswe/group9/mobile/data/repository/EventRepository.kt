package com.bounswe.group9.mobile.data.repository

import android.util.Log
import com.bounswe.group9.mobile.data.remote.AttendanceRequest
import com.bounswe.group9.mobile.data.remote.CategoryDto
import com.bounswe.group9.mobile.data.remote.EventDetailDto
import com.bounswe.group9.mobile.data.remote.EventLimitedDto
import com.bounswe.group9.mobile.data.remote.EventListResponse
import com.bounswe.group9.mobile.data.remote.RetrofitProvider
import com.google.gson.Gson

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

    suspend fun getEventDetail(
        token: String?,
        eventId: String
    ): Result<EventDetailResult> {
        return try {
            val authHeader = token?.let { "Bearer $it" }
            var response = RetrofitProvider.apiService.getEventDetail(eventId, authHeader)
            // Retry without auth on 401 — stale token should fall back to guest view
            if (response.code() == 401 && token != null) {
                Log.w("EventRepository", "Token rejected (401), retrying event detail without auth")
                response = RetrofitProvider.apiService.getEventDetail(eventId, null)
            }
            if (!response.isSuccessful) {
                val body = response.errorBody()?.string() ?: "Unknown error"
                Log.e("EventRepository", "getEventDetail HTTP ${response.code()}: $body")
                return Result.failure(Exception("${response.code()}: $body"))
            }
            val json = response.body()
                ?: return Result.failure(Exception("Empty response body"))
            val gson = Gson()
            // Full detail has "description" field; limited does not
            if (json.has("description")) {
                val detail = gson.fromJson(json, EventDetailDto::class.java)
                Result.success(EventDetailResult.Full(detail))
            } else {
                val limited = gson.fromJson(json, EventLimitedDto::class.java)
                Result.success(EventDetailResult.Limited(limited))
            }
        } catch (e: Exception) {
            Log.e("EventRepository", "getEventDetail failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    // ── Bookmark ──

    suspend fun addBookmark(token: String, eventId: String): Result<Unit> {
        return try {
            RetrofitProvider.apiService.createBookmark(eventId, "Bearer $token")
            Result.success(Unit)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("EventRepository", "addBookmark HTTP ${e.code()}: $body")
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("EventRepository", "addBookmark failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun removeBookmark(token: String, eventId: String): Result<Unit> {
        return try {
            RetrofitProvider.apiService.removeBookmark(eventId, "Bearer $token")
            Result.success(Unit)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("EventRepository", "removeBookmark HTTP ${e.code()}: $body")
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("EventRepository", "removeBookmark failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    // ── Attendance ──

    suspend fun setAttendance(token: String, eventId: String, status: String): Result<Unit> {
        return try {
            RetrofitProvider.apiService.setAttendance(eventId, "Bearer $token", AttendanceRequest(status))
            Result.success(Unit)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("EventRepository", "setAttendance HTTP ${e.code()}: $body")
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("EventRepository", "setAttendance failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun removeAttendance(token: String, eventId: String): Result<Unit> {
        return try {
            RetrofitProvider.apiService.removeAttendance(eventId, "Bearer $token")
            Result.success(Unit)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("EventRepository", "removeAttendance HTTP ${e.code()}: $body")
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("EventRepository", "removeAttendance failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    // ── Comments ──

    suspend fun getComments(eventId: String, page: Int = 1): Result<com.bounswe.group9.mobile.data.remote.CommentListResponseDto> {
        return try {
            val response = RetrofitProvider.apiService.getComments(eventId, page)
            Result.success(response)
        } catch (e: Exception) {
            Log.e("EventRepository", "getComments failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun postComment(token: String, eventId: String, text: String): Result<com.bounswe.group9.mobile.data.remote.CommentDto> {
        return try {
            val comment = RetrofitProvider.apiService.postComment(
                eventId, "Bearer $token", com.bounswe.group9.mobile.data.remote.CommentCreateRequest(text)
            )
            Result.success(comment)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun deleteComment(token: String, eventId: String, commentId: String): Result<Unit> {
        return try {
            RetrofitProvider.apiService.deleteComment(eventId, commentId, "Bearer $token")
            Result.success(Unit)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    // ── Categories ──

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

sealed class EventDetailResult {
    data class Full(val detail: EventDetailDto) : EventDetailResult()
    data class Limited(val preview: EventLimitedDto) : EventDetailResult()
}

/** Extract human-readable error from backend JSON error body. */
private fun parseErrorMessage(body: String, code: Int): String {
    return try {
        val json = Gson().fromJson(body, com.google.gson.JsonObject::class.java)
        json.get("detail")?.asString ?: "Error $code"
    } catch (_: Exception) {
        "Error $code"
    }
}
