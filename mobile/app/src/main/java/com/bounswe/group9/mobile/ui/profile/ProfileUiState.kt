package com.bounswe.group9.mobile.ui.profile

import com.bounswe.group9.mobile.data.remote.BookmarkedEventDto
import com.bounswe.group9.mobile.data.remote.EventListItemDto

data class ProfileUiState(
    // Stats (from host profile endpoint)
    val averageRating: Double? = null,
    val hostedEventsCount: Int = 0,
    val upcomingEventsCount: Int = 0,
    // Edit form drafts
    val editPhoneNumber: String = "",
    val editDateOfBirth: String = "",
    val editEmailVisibility: Boolean = false,
    val editPhoneVisibility: Boolean = false,
    // Hosted events
    val hostedEvents: List<EventListItemDto> = emptyList(),
    val isLoadingHostedEvents: Boolean = false,
    // Bookmarks
    val bookmarks: List<BookmarkedEventDto> = emptyList(),
    val bookmarkPage: Int = 1,
    val bookmarkTotalPages: Int = 1,
    val isLoadingBookmarks: Boolean = false,
    val isLoadingMoreBookmarks: Boolean = false,
    // Save state
    val isSaving: Boolean = false,
    val errorMessage: String? = null,
    val successMessage: String? = null
)
