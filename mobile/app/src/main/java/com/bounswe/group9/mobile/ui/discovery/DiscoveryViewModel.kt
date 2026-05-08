package com.bounswe.group9.mobile.ui.discovery

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bounswe.group9.mobile.data.repository.EventRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class DiscoveryViewModel(
    private val repository: EventRepository = EventRepository()
) : ViewModel() {

    private val _uiState = MutableStateFlow(DiscoveryUiState())
    val uiState: StateFlow<DiscoveryUiState> = _uiState.asStateFlow()

    private var token: String? = null
    private var tokenInitialized = false
    private var searchJob: Job? = null

    init {
        loadCategories()
    }

    fun setToken(t: String?) {
        if (tokenInitialized && t == token) return
        token = t
        tokenInitialized = true
        loadEvents(reset = true)
    }

    fun onSearchChange(query: String) {
        _uiState.value = _uiState.value.copy(search = query)
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            delay(400)
            loadEvents(reset = true)
        }
    }

    fun onCategorySelected(categoryId: String?) {
        val new = if (_uiState.value.selectedCategoryId == categoryId) null else categoryId
        _uiState.value = _uiState.value.copy(selectedCategoryId = new)
    }

    fun onQuickFilterSelected(filter: String?) {
        val new = if (_uiState.value.selectedQuickFilter == filter) null else filter
        _uiState.value = _uiState.value.copy(selectedQuickFilter = new)
    }

    fun onBookmarkedOnlyToggle() {
        _uiState.value = _uiState.value.copy(
            bookmarkedOnly = !_uiState.value.bookmarkedOnly,
            goingOnly = false
        )
    }

    fun onGoingOnlyToggle() {
        _uiState.value = _uiState.value.copy(
            goingOnly = !_uiState.value.goingOnly,
            bookmarkedOnly = false
        )
    }

    fun onSuggestedToggle() {
        // Auth-only — guard at the call site as well, but defensive here too.
        if (token == null) return
        // State-only toggle, like the other quick-filter chips. The user applies the
        // change via the "Apply" button (applyFilters), which triggers loadEvents.
        // Always clear stale fallback flag — the next response will repopulate it.
        _uiState.value = _uiState.value.copy(
            suggestedActive = !_uiState.value.suggestedActive,
            suggestedFallback = false,
            suggestedFallbackReason = null
        )
    }

    // Accessibility toggles
    fun onWheelchairToggle() {
        _uiState.value = _uiState.value.copy(wheelchair = !_uiState.value.wheelchair)
    }

    fun onAccessibleRestroomToggle() {
        _uiState.value = _uiState.value.copy(accessibleRestroom = !_uiState.value.accessibleRestroom)
    }

    fun onElevatorToggle() {
        _uiState.value = _uiState.value.copy(elevator = !_uiState.value.elevator)
    }

    fun onSeatingToggle() {
        _uiState.value = _uiState.value.copy(seating = !_uiState.value.seating)
    }

    fun onCaptionsToggle() {
        _uiState.value = _uiState.value.copy(captions = !_uiState.value.captions)
    }

    fun onQuietFriendlyToggle() {
        _uiState.value = _uiState.value.copy(quietFriendly = !_uiState.value.quietFriendly)
    }

    fun disableProximitySort() {
        _uiState.value = _uiState.value.copy(
            proximitySort = false,
            nearLat = null,
            nearLng = null
        )
    }

    fun enableProximitySort(lat: Double, lng: Double) {
        _uiState.value = _uiState.value.copy(
            proximitySort = true,
            nearLat = lat,
            nearLng = lng
        )
        loadEvents(reset = true)
    }

    fun enableProximitySortOptimistic() {
        _uiState.value = _uiState.value.copy(proximitySort = true)
    }

    fun revertProximitySort() {
        _uiState.value = _uiState.value.copy(proximitySort = false, nearLat = null, nearLng = null)
    }

    fun applyFilters() {
        loadEvents(reset = true)
    }

    fun loadNextPage() {
        val state = _uiState.value
        if (state.isLoadingMore || state.currentPage >= state.totalPages) return
        loadEvents(reset = false)
    }

    fun refresh() = loadEvents(reset = true)

    fun toggleBookmark(eventId: String) {
        val t = token ?: return
        val events = _uiState.value.events
        val event = events.find { it.id == eventId } ?: return
        val isBookmarked = event.is_bookmarked == true

        _uiState.value = _uiState.value.copy(
            events = events.map { if (it.id == eventId) it.copy(is_bookmarked = !isBookmarked) else it }
        )

        viewModelScope.launch {
            val result = if (isBookmarked) repository.removeBookmark(t, eventId)
                         else repository.addBookmark(t, eventId)
            result.onFailure {
                _uiState.value = _uiState.value.copy(
                    events = _uiState.value.events.map {
                        if (it.id == eventId) it.copy(is_bookmarked = isBookmarked) else it
                    }
                )
            }
        }
    }

    fun clearFilters() {
        _uiState.value = _uiState.value.copy(
            selectedCategoryId = null,
            selectedQuickFilter = null,
            bookmarkedOnly = false,
            goingOnly = false,
            wheelchair = false,
            accessibleRestroom = false,
            elevator = false,
            seating = false,
            captions = false,
            quietFriendly = false,
            proximitySort = false,
            nearLat = null,
            nearLng = null,
            suggestedActive = false,
            suggestedFallback = false,
            suggestedFallbackReason = null
        )
        loadEvents(reset = true)
    }

    fun activeFilterCount(): Int {
        val s = _uiState.value
        var count = 0
        if (s.selectedQuickFilter != null) count++
        if (s.selectedCategoryId != null) count++
        if (s.bookmarkedOnly) count++
        if (s.goingOnly) count++
        if (s.wheelchair) count++
        if (s.accessibleRestroom) count++
        if (s.elevator) count++
        if (s.seating) count++
        if (s.captions) count++
        if (s.quietFriendly) count++
        if (s.proximitySort) count++
        if (s.suggestedActive) count++
        return count
    }

    private fun loadEvents(reset: Boolean) {
        val state = _uiState.value
        val page = if (reset) 1 else state.currentPage + 1

        _uiState.value = if (reset)
            state.copy(isLoading = true, errorMessage = null)
        else
            state.copy(isLoadingMore = true)

        viewModelScope.launch {
            repository.getEvents(
                token = token,
                search = state.search.takeIf { it.isNotBlank() },
                categoryId = state.selectedCategoryId,
                quickFilter = state.selectedQuickFilter,
                wheelchair = state.wheelchair.takeIf { it },
                accessibleRestroom = state.accessibleRestroom.takeIf { it },
                elevator = state.elevator.takeIf { it },
                seating = state.seating.takeIf { it },
                captions = state.captions.takeIf { it },
                quietFriendly = state.quietFriendly.takeIf { it },
                sort = if (state.proximitySort && state.nearLat != null) "distance" else null,
                nearLat = state.nearLat,
                nearLng = state.nearLng,
                // Suggested only goes to the wire when the chip is on AND the user is signed in.
                suggested = if (state.suggestedActive && token != null) true else null,
                page = page
            ).fold(
                onSuccess = { response ->
                    val newEvents = if (reset) response.items
                                   else state.events + response.items
                    _uiState.value = _uiState.value.copy(
                        events = newEvents,
                        currentPage = response.page,
                        totalPages = response.total_pages,
                        isLoading = false,
                        isLoadingMore = false,
                        errorMessage = null,
                        // Only meaningful when the user actually asked for suggested.
                        suggestedFallback = if (state.suggestedActive) response.suggested_fallback else false,
                        suggestedFallbackReason = if (state.suggestedActive) response.suggested_fallback_reason else null
                    )
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isLoadingMore = false,
                        errorMessage = e.message
                    )
                }
            )
        }
    }

    private fun loadCategories() {
        viewModelScope.launch {
            repository.getCategories().onSuccess { cats ->
                _uiState.value = _uiState.value.copy(categories = cats)
            }
        }
    }
}
