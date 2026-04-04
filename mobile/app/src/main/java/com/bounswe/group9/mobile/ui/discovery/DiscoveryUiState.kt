package com.bounswe.group9.mobile.ui.discovery

import com.bounswe.group9.mobile.data.remote.CategoryDto
import com.bounswe.group9.mobile.data.remote.EventListItemDto

data class DiscoveryUiState(
    val events: List<EventListItemDto> = emptyList(),
    val categories: List<CategoryDto> = emptyList(),
    val search: String = "",
    val selectedCategoryId: String? = null,
    val selectedTemporal: String? = null, // "today" | "this_week" | "upcoming"
    val bookmarkedOnly: Boolean = false,
    val goingOnly: Boolean = false,
    val isLoading: Boolean = false,
    val isLoadingMore: Boolean = false,
    val errorMessage: String? = null,
    val currentPage: Int = 1,
    val totalPages: Int = 1
) {
    /** Client-side filter applied on top of server results. */
    val displayedEvents: List<EventListItemDto> get() = events.filter { event ->
        (!bookmarkedOnly || event.is_bookmarked == true) &&
        (!goingOnly || event.attendance_status == "going")
    }
}
