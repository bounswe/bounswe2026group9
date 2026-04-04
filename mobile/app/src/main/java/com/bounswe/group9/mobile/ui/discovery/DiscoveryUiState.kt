package com.bounswe.group9.mobile.ui.discovery

import com.bounswe.group9.mobile.data.remote.CategoryDto
import com.bounswe.group9.mobile.data.remote.EventListItemDto

data class DiscoveryUiState(
    val events: List<EventListItemDto> = emptyList(),
    val categories: List<CategoryDto> = emptyList(),
    val search: String = "",
    val selectedCategoryId: String? = null,
    val selectedTemporal: String? = null, // "today" | "this_week" | "weekend"
    val isLoading: Boolean = false,
    val isLoadingMore: Boolean = false,
    val errorMessage: String? = null,
    val currentPage: Int = 1,
    val totalPages: Int = 1
)
