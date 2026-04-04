package com.bounswe.group9.mobile.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
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

    @GET("categories")
    suspend fun getCategories(): List<CategoryDto>
}
