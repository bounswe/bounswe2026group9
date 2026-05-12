package com.bounswe.group9.mobile.ui.discovery

import com.bounswe.group9.mobile.data.remote.CategoryDto
import com.bounswe.group9.mobile.data.remote.EventListItemDto

data class DiscoveryUiState(
    val events: List<EventListItemDto> = emptyList(),
    val categories: List<CategoryDto> = emptyList(),
    val search: String = "",
    // Multi-select: empty = no filter, size == 1 → sent to API, size >= 2 → client-side filtered
    val selectedCategoryIds: Set<String> = emptySet(),
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
    // Explicit sort: "start_time" | "category" | null (null = server default)
    // "distance" sort is handled separately via proximitySort + GPS coords below.
    val selectedSort: String? = null,
    // Proximity ranking: sort=distance using device GPS coords
    val proximitySort: Boolean = false,
    val nearLat: Double? = null,
    val nearLng: Double? = null,
    // "Suggested for you" — biases listing toward categories the user has previously attended.
    // Auth-only; chip is hidden for guests.
    val suggestedActive: Boolean = false,
    /** Server flag: true when the user has no past-attendance history so the response fell back to default ordering. */
    val suggestedFallback: Boolean = false,
    /** "no_history" | "no_match" | null — reason for fallback; null means suggestions are active. */
    val suggestedFallbackReason: String? = null,
    val isLoading: Boolean = false,
    val isLoadingMore: Boolean = false,
    val errorMessage: String? = null,
    val currentPage: Int = 1,
    val totalPages: Int = 1
) {
    val hasAccessibilityFilter: Boolean get() =
        wheelchair || accessibleRestroom || elevator || seating || captions || quietFriendly

    /**
     * Client-side filters applied on top of the server response:
     * - bookmarkedOnly / goingOnly (personal filters the API can't gate directly)
     * - multi-category (when 2+ selected the API returns unfiltered results so we filter here)
     */
    val displayedEvents: List<EventListItemDto> get() = events.filter { event ->
        (!bookmarkedOnly || event.is_bookmarked == true) &&
        (!goingOnly || event.attendance_status == "going") &&
        (selectedCategoryIds.size <= 1 ||
            event.categories.any { it.id in selectedCategoryIds })
    }
}
