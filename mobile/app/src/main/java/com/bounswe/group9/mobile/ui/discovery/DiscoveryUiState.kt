package com.bounswe.group9.mobile.ui.discovery

import com.bounswe.group9.mobile.data.remote.CategoryDto
import com.bounswe.group9.mobile.data.remote.EventListItemDto

data class DiscoveryUiState(
    val events: List<EventListItemDto> = emptyList(),
    val categories: List<CategoryDto> = emptyList(),
    val search: String = "",
    val selectedCategoryId: String? = null,
    // quick_filter: "now"|"today"|"weekend"|"upcoming"|"this_week"|"past"|null
    val selectedQuickFilter: String? = null,
    val bookmarkedOnly: Boolean = false,
    val goingOnly: Boolean = false,
    // Accessibility filters
    val wheelchair: Boolean = false,
    val accessibleRestroom: Boolean = false,
    val elevator: Boolean = false,
    val seating: Boolean = false,
    val captions: Boolean = false,
    val quietFriendly: Boolean = false,
    // Proximity ranking: sort=distance using device GPS coords
    val proximitySort: Boolean = false,
    val nearLat: Double? = null,
    val nearLng: Double? = null,
    val isLoading: Boolean = false,
    val isLoadingMore: Boolean = false,
    val errorMessage: String? = null,
    val currentPage: Int = 1,
    val totalPages: Int = 1
) {
    val hasAccessibilityFilter: Boolean get() =
        wheelchair || accessibleRestroom || elevator || seating || captions || quietFriendly

    /** Client-side filter for bookmarked/going (server handles everything else). */
    val displayedEvents: List<EventListItemDto> get() = events.filter { event ->
        (!bookmarkedOnly || event.is_bookmarked == true) &&
        (!goingOnly || event.attendance_status == "going")
    }
}
