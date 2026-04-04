package com.bounswe.group9.mobile.data.remote

import com.google.gson.JsonObject
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

// ── Auth ──────────────────────────────────────────────────────────────────────

data class LoginRequest(val email: String, val password: String)

data class RegisterRequest(
    val username: String,
    val email: String,
    val password: String,
    val date_of_birth: String
)

data class UserResponse(val id: String, val username: String, val email: String)

data class AuthResponse(
    val user: UserResponse,
    val access_token: String,
    val token_type: String
)

// ── Events ────────────────────────────────────────────────────────────────────

data class CategoryDto(
    val id: String,
    val name: String,
    val is_predefined: Boolean,
    val is_approved: Boolean
)

data class EventLocationDto(
    val id: String,
    val name: String,
    val latitude: Double,
    val longitude: Double,
    val is_primary: Boolean,
    val order_index: Int
)

data class EventListItemDto(
    val id: String,
    val host_id: String,
    val title: String,
    val description: String?,
    val start_datetime: String,
    val end_datetime: String,
    val visibility: String,
    val is_age_restricted: Boolean,
    val attendee_limit: Int?,
    val attendee_count: Int,
    val status: String,
    val is_bookmarked: Boolean?,
    val attendance_status: String?,
    val going_count: Int,
    val interested_count: Int,
    val is_full: Boolean?,
    val categories: List<CategoryDto>,
    val primary_location: EventLocationDto?,
    val primary_image_url: String?
)

data class EventListResponse(
    val items: List<EventListItemDto>,
    val total: Int,
    val page: Int,
    val page_size: Int,
    val total_pages: Int
)

// ── Bookmark & Attendance ─────────────────────────────────────────────────────

data class BookmarkResponse(val id: String, val event_id: String, val created_at: String)
data class AttendanceRequest(val status: String) // "going" or "interested"
data class AttendanceResponse(val id: String, val event_id: String, val user_id: String, val status: String, val marked_at: String)
data class MessageResponse(val message: String)

// ── API Interface ─────────────────────────────────────────────────────────────

data class RefreshTokenRequest(val refresh_token: String?)

interface ApiService {
    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): AuthResponse

    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequest): AuthResponse

    @POST("auth/refresh")
    suspend fun refresh(@Body body: RefreshTokenRequest = RefreshTokenRequest(null)): AuthResponse

    @GET("events")
    suspend fun getEvents(
        @Header("Authorization") token: String? = null,
        @Query("search") search: String? = null,
        @Query("category_id") categoryId: String? = null,
        @Query("temporal_filter") temporalFilter: String? = null,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20
    ): EventListResponse

    @GET("events/{event_id}")
    suspend fun getEventDetail(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String? = null
    ): Response<JsonObject>

    // ── Bookmark ──

    @POST("events/{event_id}/bookmark")
    suspend fun createBookmark(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String
    ): BookmarkResponse

    @DELETE("events/{event_id}/bookmark")
    suspend fun removeBookmark(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String
    ): MessageResponse

    // ── Attendance ──

    @POST("events/{event_id}/attendance")
    suspend fun setAttendance(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String,
        @Body body: AttendanceRequest
    ): AttendanceResponse

    @DELETE("events/{event_id}/attendance")
    suspend fun removeAttendance(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String
    ): MessageResponse

    @GET("categories")
    suspend fun getCategories(): List<CategoryDto>
}
