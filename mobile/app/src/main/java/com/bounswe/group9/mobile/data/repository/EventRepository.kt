package com.bounswe.group9.mobile.data.repository

import android.util.Log
import com.bounswe.group9.mobile.data.remote.AttendanceRequest
import com.bounswe.group9.mobile.data.remote.CategoryDto
import com.bounswe.group9.mobile.data.remote.EventDetailDto
import com.bounswe.group9.mobile.data.remote.EventListItemDto
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
                return Result.failure(parseEventDetailError(response.code(), body))
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

    suspend fun getSimilarEvents(
        eventId: String,
        token: String? = null
    ): Result<List<EventListItemDto>> {
        return try {
            val authHeader = token?.let { "Bearer $it" }
            val response = RetrofitProvider.apiService.getSimilarEvents(eventId, authHeader)
            if (!response.isSuccessful) {
                val body = response.errorBody()?.string() ?: "Unknown error"
                Log.e("EventRepository", "getSimilarEvents HTTP ${response.code()}: $body")
                return Result.failure(Exception("${response.code()}: $body"))
            }
            Result.success(response.body() ?: emptyList())
        } catch (e: Exception) {
            Log.e("EventRepository", "getSimilarEvents failed: ${e.message}", e)
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

    // ── Profile Update (DOB) ──

    suspend fun updateDateOfBirth(token: String, dateOfBirth: String): Result<Unit> {
        return try {
            RetrofitProvider.apiService.updateProfile(
                "Bearer $token", mapOf("date_of_birth" to dateOfBirth)
            )
            Result.success(Unit)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    // ── Event CRUD ──

    suspend fun createEvent(token: String, request: com.bounswe.group9.mobile.data.remote.EventCreateRequest): Result<EventDetailDto> {
        return try {
            val response = RetrofitProvider.apiService.createEvent("Bearer $token", request)
            if (!response.isSuccessful) {
                val body = response.errorBody()?.string() ?: "Unknown error"
                return Result.failure(Exception(parseErrorMessage(body, response.code())))
            }
            val json = response.body() ?: return Result.failure(Exception("Empty response"))
            Result.success(Gson().fromJson(json, EventDetailDto::class.java))
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("EventRepository", "createEvent failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun updateEvent(token: String, eventId: String, request: com.bounswe.group9.mobile.data.remote.EventUpdateRequest): Result<EventDetailDto> {
        return try {
            val response = RetrofitProvider.apiService.updateEvent(eventId, "Bearer $token", request)
            if (!response.isSuccessful) {
                val body = response.errorBody()?.string() ?: "Unknown error"
                return Result.failure(Exception(parseErrorMessage(body, response.code())))
            }
            val json = response.body() ?: return Result.failure(Exception("Empty response"))
            Result.success(Gson().fromJson(json, EventDetailDto::class.java))
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("EventRepository", "updateEvent failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun changeEventStatus(token: String, eventId: String, status: String): Result<EventDetailDto> {
        return try {
            val response = RetrofitProvider.apiService.changeEventStatus(
                eventId, "Bearer $token",
                com.bounswe.group9.mobile.data.remote.EventStatusRequest(status)
            )
            if (!response.isSuccessful) {
                val body = response.errorBody()?.string() ?: "Unknown error"
                return Result.failure(Exception(parseErrorMessage(body, response.code())))
            }
            val json = response.body() ?: return Result.failure(Exception("Empty response"))
            Result.success(Gson().fromJson(json, EventDetailDto::class.java))
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("EventRepository", "changeEventStatus failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun deleteEvent(token: String, eventId: String): Result<Unit> {
        return try {
            val response = RetrofitProvider.apiService.deleteEvent(eventId, "Bearer $token")
            if (!response.isSuccessful) {
                val body = response.errorBody()?.string() ?: "Unknown error"
                return Result.failure(Exception(parseErrorMessage(body, response.code())))
            }
            Result.success(Unit)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("EventRepository", "deleteEvent failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun uploadEventImage(token: String, eventId: String, part: okhttp3.MultipartBody.Part): Result<com.bounswe.group9.mobile.data.remote.EventImageDto> {
        return try {
            val response = RetrofitProvider.apiService.uploadEventImage(eventId, "Bearer $token", part)
            if (!response.isSuccessful) {
                val body = response.errorBody()?.string() ?: "Unknown error"
                return Result.failure(Exception(parseErrorMessage(body, response.code())))
            }
            val json = response.body() ?: return Result.failure(Exception("Empty response"))
            val gson = Gson()
            Result.success(gson.fromJson(json, com.bounswe.group9.mobile.data.remote.EventImageDto::class.java))
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("EventRepository", "uploadEventImage failed: ${e.message}", e)
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

    // ── Invites ──

    suspend fun createInvite(token: String, eventId: String): Result<com.bounswe.group9.mobile.data.remote.InviteResponseDto> {
        return try {
            Result.success(RetrofitProvider.apiService.createInvite(eventId, "Bearer $token"))
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun listInvites(token: String, eventId: String): Result<com.bounswe.group9.mobile.data.remote.InviteListResponseDto> {
        return try {
            Result.success(RetrofitProvider.apiService.listInvites(eventId, "Bearer $token"))
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun acceptInvite(token: String, eventId: String, inviteToken: String): Result<Unit> {
        return try {
            RetrofitProvider.apiService.acceptInvite(eventId, inviteToken, "Bearer $token")
            Result.success(Unit)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) { Result.failure(e) }
    }

    // ── Access Requests ──

    suspend fun requestAccess(token: String, eventId: String): Result<com.bounswe.group9.mobile.data.remote.AccessRequestResponseDto> {
        return try {
            Result.success(RetrofitProvider.apiService.createAccessRequest(eventId, "Bearer $token"))
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun listAccessRequests(token: String, eventId: String): Result<com.bounswe.group9.mobile.data.remote.AccessRequestListResponseDto> {
        return try {
            Result.success(RetrofitProvider.apiService.listAccessRequests(eventId, "Bearer $token"))
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun decideAccessRequest(token: String, eventId: String, requestId: String, decision: String): Result<com.bounswe.group9.mobile.data.remote.AccessRequestResponseDto> {
        return try {
            Result.success(RetrofitProvider.apiService.decideAccessRequest(eventId, requestId, "Bearer $token", com.bounswe.group9.mobile.data.remote.AccessRequestDecisionDto(decision)))
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) { Result.failure(e) }
    }
}

sealed class EventDetailResult {
    data class Full(val detail: EventDetailDto) : EventDetailResult()
    data class Limited(val preview: EventLimitedDto) : EventDetailResult()
}

/** Typed error for event detail — allows UI to show specific screens. */
sealed class EventDetailError(message: String) : Exception(message) {
    class NotFound : EventDetailError("Event not found")
    class Underage : EventDetailError("You must be 18 or older to view this event")
    class DobRequired : EventDetailError("Date of birth is required to view age-restricted events")
    class Generic(message: String) : EventDetailError(message)
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

/** Parse HTTP error into typed EventDetailError. */
private fun parseEventDetailError(code: Int, body: String): EventDetailError {
    val message = parseErrorMessage(body, code)
    return when {
        code == 404 -> EventDetailError.NotFound()
        code == 403 && message.contains("18", ignoreCase = true) -> EventDetailError.Underage()
        code == 403 && message.contains("date of birth", ignoreCase = true) -> EventDetailError.DobRequired()
        else -> EventDetailError.Generic(message)
    }
}
