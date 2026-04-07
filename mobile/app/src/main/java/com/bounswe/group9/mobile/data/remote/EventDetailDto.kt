package com.bounswe.group9.mobile.data.remote

/**
 * Full detail response from GET /events/{event_id} for authenticated users
 * viewing public events (or host/granted users viewing private events).
 */
data class EventDetailDto(
    val id: String,
    val host_id: String,
    val host_username: String? = null,
    val title: String,
    val description: String,
    val start_datetime: String,
    val end_datetime: String,
    val visibility: String,
    val is_age_restricted: Boolean,
    val attendee_limit: Int?,
    val attendee_count: Int,
    val status: String,
    val created_at: String,
    val updated_at: String,
    val is_bookmarked: Boolean?,
    val attendance_status: String?,
    val going_count: Int,
    val bookmark_count: Int = 0,
    val is_full: Boolean?,
    val locations: List<EventLocationDto>,
    val categories: List<CategoryDto>,
    val images: List<EventImageDto>,
    val venue_metadata: VenueMetadataDto?,
    val equipment_requirements: List<EquipmentDto>
)

data class EventImageDto(
    val id: String,
    val image_url: String,
    val upload_date: String
)

data class VenueMetadataDto(
    val id: String,
    val price: String?,
    val language: String?,
    val health_requirements: String?,
    val wheelchair_access: Boolean,
    val accessible_restroom: Boolean,
    val elevator_available: Boolean,
    val seating_available: Boolean,
    val captions_support: Boolean,
    val quiet_friendly: Boolean
)

data class EquipmentDto(
    val id: String,
    val item_name: String,
    val is_required: Boolean
)

/**
 * Limited preview response for guests or private/cancelled events.
 * Gson will set missing fields to defaults (null/false/0).
 */
data class EventLimitedDto(
    val id: String,
    val title: String,
    val start_datetime: String,
    val end_datetime: String,
    val visibility: String,
    val is_age_restricted: Boolean,
    val status: String,
    val is_bookmarked: Boolean?,
    val access_request_status: String? = null,  // "pending" | "approved" | "rejected" | null
    val categories: List<CategoryDto>
)
