package com.bounswe.group9.mobile.data.remote

import com.google.gson.JsonObject
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
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
    val order_index: Int,
    val location_address: String? = null
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
    val bookmark_count: Int = 0,
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

// ── Comments ─────────────────────────────────────────────────────────────────

data class CommentAuthorDto(val id: String, val username: String)

data class CommentDto(
    val id: String,
    val event_id: String,
    val user: CommentAuthorDto,
    val text: String,
    val created_at: String,
    val parent_id: String? = null,
    val replies: List<CommentDto> = emptyList()
)

data class CommentListResponseDto(
    val items: List<CommentDto>,
    val total: Int,
    val page: Int,
    val page_size: Int,
    val total_pages: Int
)

data class CommentCreateRequest(val text: String)

// ── Host Profile & Rating ────────────────────────────────────────────────────

data class HostProfileDto(
    val id: String,
    val username: String,
    val email: String?,
    val phone_number: String?,
    val average_rating: Double?,
    val hosted_events_count: Int,
    val hosted_events: List<EventListItemDto>,
    val can_rate: Boolean = false
)

data class RatingRequest(val score: Double)

data class RatingResponseDto(
    val id: String,
    val rater_id: String,
    val host_id: String,
    val score: Double,
    val created_at: String
)

// ── Notifications ─────────────────────────────────────────────────────────────

data class NotificationDto(
    val id: String,
    val user_id: String,
    val event_id: String?,
    val type: String,
    val message: String,
    val is_read: Boolean,
    val created_at: String
)

data class NotificationListResponseDto(
    val items: List<NotificationDto>,
    val total: Int,
    val unread_count: Int = 0,
    val page: Int,
    val page_size: Int,
    val total_pages: Int
)

data class NotificationReadResponseDto(val id: String, val is_read: Boolean)
data class NotificationReadAllResponseDto(val updated_count: Int)

// ── My Profile ────────────────────────────────────────────────────────────────

data class ProfileUpdateRequestDto(
    val phone_number: String? = null,
    val date_of_birth: String? = null,
    val email_visibility: String? = null,
    val phone_visibility: String? = null,
    val default_location_name: String? = null,
    val default_location_lat: Double? = null,
    val default_location_lng: Double? = null
)

data class MyProfileDto(
    val id: String,
    val username: String,
    val email: String,
    val phone_number: String? = null,
    val date_of_birth: String? = null,
    val email_visibility: Boolean = false,
    val phone_visibility: Boolean = false,
    val role: String = "",
    val is_active: Boolean = true
)

data class BookmarkedEventDto(
    val id: String,
    val title: String,
    val start_datetime: String,
    val end_datetime: String,
    val visibility: String,
    val is_age_restricted: Boolean,
    val status: String,
    val categories: List<CategoryDto> = emptyList(),
    val primary_location: EventLocationDto? = null,
    val primary_image_url: String? = null,
    val bookmarked_at: String
)

data class BookmarkListResponseDto(
    val items: List<BookmarkedEventDto>,
    val total: Int,
    val page: Int,
    val page_size: Int,
    val total_pages: Int
)

// ── Invites & Access Requests ─────────────────────────────────────────────────

data class InviteCreateRequestDto(
    val max_uses: Int? = null,
    val expires_in_hours: Int? = null
)

data class InviteResponseDto(
    val id: String,
    val event_id: String,
    val token: String,
    val invite_url: String,
    val expires_at: String?,
    val max_uses: Int?,
    val use_count: Int,
    val created_at: String
)

data class InviteListResponseDto(
    val items: List<InviteResponseDto>
)

data class AccessRequestResponseDto(
    val id: String,
    val event_id: String,
    val user_id: String,
    val username: String,
    val status: String,  // "pending" | "approved" | "rejected"
    val created_at: String,
    val resolved_at: String?
)

data class AccessRequestListResponseDto(
    val items: List<AccessRequestResponseDto>
)

data class AccessRequestDecisionDto(val status: String) // "approved" | "rejected"

// ── Event Create / Edit DTOs ──────────────────────────────────────────────────

data class LocationRequest(
    val name: String,
    val latitude: Double,
    val longitude: Double,
    val is_primary: Boolean = true,
    val order_index: Int = 0,
    val location_address: String? = null
)

data class SegmentRequest(
    val location_index: Int,
    val order_index: Int,
    val start_datetime: String,
    val end_datetime: String,
    val description: String? = null
)

data class VenueMetadataRequest(
    val health_requirements: String? = null,
    val wheelchair_access: Boolean = false,
    val accessible_restroom: Boolean = false,
    val elevator_available: Boolean = false,
    val seating_available: Boolean = false,
    val captions_support: Boolean = false,
    val quiet_friendly: Boolean = false
)

data class EventCreateRequest(
    val title: String,
    val description: String,
    val start_datetime: String,        // ISO-8601
    val end_datetime: String,          // ISO-8601
    val visibility: String = "public", // "public" | "private"
    val is_age_restricted: Boolean = false,
    val attendee_limit: Int? = null,
    val status: String = "draft",      // "draft" | "published"
    val category_ids: List<String>,
    val locations: List<LocationRequest>,
    val segments: List<SegmentRequest>? = null,
    val venue_metadata: VenueMetadataRequest? = null
)

data class EventUpdateRequest(
    val title: String? = null,
    val description: String? = null,
    val start_datetime: String? = null,
    val end_datetime: String? = null,
    val visibility: String? = null,
    val is_age_restricted: Boolean? = null,
    val attendee_limit: Int? = null,
    val clear_attendee_limit: Boolean = false,
    val category_ids: List<String>? = null,
    val locations: List<LocationRequest>? = null,
    val segments: List<SegmentRequest>? = null,
    val venue_metadata: VenueMetadataRequest? = null
)

data class EventStatusRequest(val status: String) // "published" | "cancelled" | "ended"

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
        @Query("quick_filter") quickFilter: String? = null,
        @Query("start_after") startAfter: String? = null,
        @Query("end_before") endBefore: String? = null,
        @Query("near_lat") nearLat: Double? = null,
        @Query("near_lng") nearLng: Double? = null,
        @Query("radius_km") radiusKm: Double? = null,
        @Query("use_default_area") useDefaultArea: Boolean? = null,
        @Query("wheelchair") wheelchair: Boolean? = null,
        @Query("accessible_restroom") accessibleRestroom: Boolean? = null,
        @Query("elevator") elevator: Boolean? = null,
        @Query("seating") seating: Boolean? = null,
        @Query("captions") captions: Boolean? = null,
        @Query("quiet_friendly") quietFriendly: Boolean? = null,
        @Query("sort") sort: String? = null,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20
    ): EventListResponse

    @GET("events/{event_id}")
    suspend fun getEventDetail(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String? = null
    ): Response<JsonObject>

    @GET("events/{event_id}/similar")
    suspend fun getSimilarEvents(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String? = null
    ): Response<List<EventListItemDto>>

    // ── Event CRUD ──

    @POST("events")
    suspend fun createEvent(
        @Header("Authorization") token: String,
        @Body body: EventCreateRequest
    ): Response<JsonObject>

    @PUT("events/{event_id}")
    suspend fun updateEvent(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String,
        @Body body: EventUpdateRequest
    ): Response<JsonObject>

    @PATCH("events/{event_id}/status")
    suspend fun changeEventStatus(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String,
        @Body body: EventStatusRequest
    ): Response<JsonObject>

    @DELETE("events/{event_id}")
    suspend fun deleteEvent(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String
    ): Response<JsonObject>

    // ── Image Upload ──

    @Multipart
    @POST("events/{event_id}/images")
    suspend fun uploadEventImage(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String,
        @Part file: MultipartBody.Part
    ): Response<JsonObject>



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

    // ── Comments ──

    @GET("events/{event_id}/comments")
    suspend fun getComments(
        @Path("event_id") eventId: String,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20
    ): CommentListResponseDto

    @POST("events/{event_id}/comments")
    suspend fun postComment(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String,
        @Body body: CommentCreateRequest
    ): CommentDto

    @DELETE("events/{event_id}/comments/{comment_id}")
    suspend fun deleteComment(
        @Path("event_id") eventId: String,
        @Path("comment_id") commentId: String,
        @Header("Authorization") token: String
    ): MessageResponse

    // ── Host Profile & Rating ──

    @GET("users/{user_id}/profile")
    suspend fun getHostProfile(
        @Path("user_id") userId: String,
        @Header("Authorization") token: String? = null
    ): HostProfileDto

    @POST("users/{host_id}/ratings")
    suspend fun rateHost(
        @Path("host_id") hostId: String,
        @Header("Authorization") token: String,
        @Body body: RatingRequest
    ): RatingResponseDto

    // ── Profile Update ──

    @PUT("users/me")
    suspend fun updateProfile(
        @Header("Authorization") token: String,
        @Body body: Map<String, String>
    ): JsonObject

    @GET("categories")
    suspend fun getCategories(): List<CategoryDto>

    // ── Notifications ──

    @GET("notifications")
    suspend fun getNotifications(
        @Header("Authorization") token: String,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20
    ): NotificationListResponseDto

    @PATCH("notifications/{notification_id}/read")
    suspend fun markNotificationRead(
        @Path("notification_id") notificationId: String,
        @Header("Authorization") token: String
    ): NotificationReadResponseDto

    @PATCH("notifications/read-all")
    suspend fun markAllNotificationsRead(
        @Header("Authorization") token: String
    ): NotificationReadAllResponseDto

    // ── My Profile ──

    @GET("auth/me")
    suspend fun getMe(
        @Header("Authorization") token: String
    ): MyProfileDto

    @PUT("users/me")
    suspend fun updateMyProfile(
        @Header("Authorization") token: String,
        @Body body: ProfileUpdateRequestDto
    ): MyProfileDto

    @GET("users/me/bookmarks")
    suspend fun getMyBookmarks(
        @Header("Authorization") token: String,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20
    ): BookmarkListResponseDto

    // ── Invites ──

    @POST("events/{event_id}/invites")
    suspend fun createInvite(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String,
        @Body body: InviteCreateRequestDto = InviteCreateRequestDto()
    ): InviteResponseDto

    @GET("events/{event_id}/invites")
    suspend fun listInvites(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String
    ): InviteListResponseDto

    @POST("events/{event_id}/invites/{token}/accept")
    suspend fun acceptInvite(
        @Path("event_id") eventId: String,
        @Path("token") token: String,
        @Header("Authorization") authToken: String
    ): MessageResponse

    // ── Access Requests ──

    @POST("events/{event_id}/access-requests")
    suspend fun createAccessRequest(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String
    ): AccessRequestResponseDto

    @GET("events/{event_id}/access-requests")
    suspend fun listAccessRequests(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String
    ): AccessRequestListResponseDto

    @PATCH("events/{event_id}/access-requests/{request_id}")
    suspend fun decideAccessRequest(
        @Path("event_id") eventId: String,
        @Path("request_id") requestId: String,
        @Header("Authorization") token: String,
        @Body body: AccessRequestDecisionDto
    ): AccessRequestResponseDto

    // ── Check-in (QR) ──

    @GET("attendances/me/{event_id}/qr")
    suspend fun getMyAttendeeQr(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String
    ): Response<AttendeeQrTokenDto>

    @POST("events/{event_id}/check-in")
    suspend fun postCheckIn(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String,
        @Body body: CheckInRequest
    ): Response<CheckInResultDto>

    @GET("events/{event_id}/attendees")
    suspend fun getEventAttendees(
        @Path("event_id") eventId: String,
        @Header("Authorization") token: String
    ): Response<List<AttendeeStatusDto>>
}
