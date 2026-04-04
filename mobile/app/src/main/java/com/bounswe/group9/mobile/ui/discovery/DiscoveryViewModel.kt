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
        _uiState.value = _uiState.value.copy(selectedCategoryId = categoryId)
        // Don't load yet — wait for applyFilters()
    }

    fun onTemporalSelected(filter: String?) {
        val new = if (_uiState.value.selectedTemporal == filter) null else filter
        _uiState.value = _uiState.value.copy(selectedTemporal = new)
        // Don't load yet — wait for applyFilters()
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

    fun clearFilters() {
        _uiState.value = _uiState.value.copy(selectedCategoryId = null, selectedTemporal = null)
        loadEvents(reset = true)
    }

    fun activeFilterCount(): Int {
        var count = 0
        if (_uiState.value.selectedTemporal != null) count++
        if (_uiState.value.selectedCategoryId != null) count++
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
                temporalFilter = state.selectedTemporal,
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
                        errorMessage = null
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
