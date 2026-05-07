package com.bounswe.group9.mobile.data.remote

/** Returned by GET /attendances/me/{eventId}/qr — the attendee's signed token to render as a QR. */
data class AttendeeQrTokenDto(
    val token: String,
    val expires_at: String? = null
)

/**
 * Body for POST /events/{eventId}/check-in. Either field may be set:
 *  - `token`: the signed payload decoded from the attendee's QR
 *  - `user_id`: a direct attendee id, used by the manual fallback when the camera fails
 *
 * Gson's default behaviour drops null fields, so the wire payload only carries the one in use.
 */
data class CheckInRequest(
    val token: String? = null,
    val user_id: String? = null
)

/** Result of a successful check-in (200). */
data class CheckInResultDto(
    val user_id: String,
    val username: String? = null,
    val checked_in_at: String
)

/** Item in GET /events/{eventId}/attendees — the host's roster with check-in status. */
data class AttendeeStatusDto(
    val user_id: String,
    val username: String,
    val checked_in_at: String? = null
)

