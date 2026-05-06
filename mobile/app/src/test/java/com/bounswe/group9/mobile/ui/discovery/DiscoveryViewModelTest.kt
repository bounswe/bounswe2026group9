package com.bounswe.group9.mobile.ui.discovery

import com.bounswe.group9.mobile.data.remote.EventListItemDto
import com.bounswe.group9.mobile.data.remote.EventListResponse
import com.bounswe.group9.mobile.data.repository.EventRepository
import com.bounswe.group9.mobile.testing.MainDispatcherExtension
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.extension.ExtendWith

@OptIn(ExperimentalCoroutinesApi::class)
@ExtendWith(MainDispatcherExtension::class)
class DiscoveryViewModelTest {

    private val repository = mockk<EventRepository>()

    @BeforeEach
    fun setUp() {
        coEvery { repository.getCategories() } returns Result.success(emptyList())
        stubGetEvents()
    }

    /** Stub `getEvents` for arbitrary args. Tests can call again to override the response. */
    private fun stubGetEvents(response: EventListResponse = emptyResponse()) {
        coEvery {
            repository.getEvents(
                token = any(), search = any(), categoryId = any(), quickFilter = any(),
                wheelchair = any(), accessibleRestroom = any(), elevator = any(),
                seating = any(), captions = any(), quietFriendly = any(),
                sort = any(), nearLat = any(), nearLng = any(), radiusKm = any(),
                page = any(), pageSize = any()
            )
        } returns Result.success(response)
    }

    private fun emptyResponse(page: Int = 1, totalPages: Int = 1) = EventListResponse(
        items = emptyList(), total = 0, page = page,
        page_size = 20, total_pages = totalPages
    )

    private fun viewModel() = DiscoveryViewModel(repository)

    @Test
    fun `setToken triggers initial load`() = runTest {
        val vm = viewModel()
        vm.setToken("tok")
        advanceUntilIdle()

        coVerify(exactly = 1) {
            repository.getEvents(
                token = "tok", search = any(), categoryId = any(), quickFilter = any(),
                wheelchair = any(), accessibleRestroom = any(), elevator = any(),
                seating = any(), captions = any(), quietFriendly = any(),
                sort = any(), nearLat = any(), nearLng = any(), radiusKm = any(),
                page = 1, pageSize = any()
            )
        }
    }

    @Test
    fun `setToken with same value twice loads only once`() = runTest {
        val vm = viewModel()
        vm.setToken("tok")
        advanceUntilIdle()
        vm.setToken("tok")
        advanceUntilIdle()

        coVerify(exactly = 1) {
            repository.getEvents(
                token = "tok", search = any(), categoryId = any(), quickFilter = any(),
                wheelchair = any(), accessibleRestroom = any(), elevator = any(),
                seating = any(), captions = any(), quietFriendly = any(),
                sort = any(), nearLat = any(), nearLng = any(), radiusKm = any(),
                page = any(), pageSize = any()
            )
        }
    }

    @Test
    fun `onSearchChange updates state immediately and reloads after debounce`() = runTest {
        val vm = viewModel()
        vm.setToken(null)
        advanceUntilIdle()

        vm.onSearchChange("jaz")
        assertEquals("jaz", vm.uiState.value.search)
        // Initial setToken triggered 1 load. The 400ms debounce keeps the
        // count at 1 until the timer expires.
        advanceTimeBy(399)
        coVerify(exactly = 1) {
            repository.getEvents(
                token = any(), search = any(), categoryId = any(), quickFilter = any(),
                wheelchair = any(), accessibleRestroom = any(), elevator = any(),
                seating = any(), captions = any(), quietFriendly = any(),
                sort = any(), nearLat = any(), nearLng = any(), radiusKm = any(),
                page = any(), pageSize = any()
            )
        }

        advanceTimeBy(2)
        advanceUntilIdle()
        coVerify(exactly = 1) {
            repository.getEvents(
                token = any(), search = "jaz", categoryId = any(), quickFilter = any(),
                wheelchair = any(), accessibleRestroom = any(), elevator = any(),
                seating = any(), captions = any(), quietFriendly = any(),
                sort = any(), nearLat = any(), nearLng = any(), radiusKm = any(),
                page = any(), pageSize = any()
            )
        }
    }

    @Test
    fun `onCategorySelected toggles the same id back to null`() {
        val vm = viewModel()
        vm.onCategorySelected("cat-1")
        assertEquals("cat-1", vm.uiState.value.selectedCategoryId)
        vm.onCategorySelected("cat-1")
        assertNull(vm.uiState.value.selectedCategoryId)
    }

    @Test
    fun `onQuickFilterSelected toggles the same value back to null`() {
        val vm = viewModel()
        vm.onQuickFilterSelected("today")
        assertEquals("today", vm.uiState.value.selectedQuickFilter)
        vm.onQuickFilterSelected("today")
        assertNull(vm.uiState.value.selectedQuickFilter)
    }

    @Test
    fun `bookmarked and going toggles are mutually exclusive`() {
        val vm = viewModel()
        vm.onBookmarkedOnlyToggle()
        vm.onGoingOnlyToggle()

        // Going turned on should clear bookmarked.
        assertTrue(vm.uiState.value.goingOnly)
        assertFalse(vm.uiState.value.bookmarkedOnly)

        vm.onBookmarkedOnlyToggle()
        assertTrue(vm.uiState.value.bookmarkedOnly)
        assertFalse(vm.uiState.value.goingOnly)
    }

    @Test
    fun `clearFilters resets every flag and reloads`() = runTest {
        val vm = viewModel()
        vm.setToken("tok")
        advanceUntilIdle()
        vm.onCategorySelected("cat-1")
        vm.onQuickFilterSelected("weekend")
        vm.onWheelchairToggle()
        vm.onBookmarkedOnlyToggle()

        vm.clearFilters()
        advanceUntilIdle()

        val state = vm.uiState.value
        assertNull(state.selectedCategoryId)
        assertNull(state.selectedQuickFilter)
        assertFalse(state.bookmarkedOnly)
        assertFalse(state.wheelchair)
        // setToken: 1 + clearFilters: 1.
        coVerify(exactly = 2) {
            repository.getEvents(
                token = any(), search = any(), categoryId = any(), quickFilter = any(),
                wheelchair = any(), accessibleRestroom = any(), elevator = any(),
                seating = any(), captions = any(), quietFriendly = any(),
                sort = any(), nearLat = any(), nearLng = any(), radiusKm = any(),
                page = any(), pageSize = any()
            )
        }
    }

    @Test
    fun `loadNextPage stops when currentPage reaches totalPages`() = runTest {
        stubGetEvents(emptyResponse(page = 1, totalPages = 1))
        val vm = viewModel()
        vm.setToken("tok")
        advanceUntilIdle()

        vm.loadNextPage()
        advanceUntilIdle()

        // Initial load only — no page 2 fetched.
        coVerify(exactly = 1) {
            repository.getEvents(
                token = any(), search = any(), categoryId = any(), quickFilter = any(),
                wheelchair = any(), accessibleRestroom = any(), elevator = any(),
                seating = any(), captions = any(), quietFriendly = any(),
                sort = any(), nearLat = any(), nearLng = any(), radiusKm = any(),
                page = any(), pageSize = any()
            )
        }
    }

    @Test
    fun `toggleBookmark optimistically flips and rolls back on failure`() = runTest {
        stubGetEvents(
            EventListResponse(
                items = listOf(sampleEvent("e1", bookmarked = false)),
                total = 1, page = 1, page_size = 20, total_pages = 1
            )
        )
        coEvery { repository.addBookmark("tok", "e1") } returns Result.failure(Exception("nope"))
        val vm = viewModel()
        vm.setToken("tok")
        advanceUntilIdle()

        vm.toggleBookmark("e1")
        // Optimistic: flips on, then on failure rolls back to false.
        advanceUntilIdle()
        assertEquals(false, vm.uiState.value.events.first { it.id == "e1" }.is_bookmarked)
    }

    @Test
    fun `activeFilterCount counts active flags`() {
        val vm = viewModel()
        assertEquals(0, vm.activeFilterCount())
        vm.onCategorySelected("cat-1")
        vm.onQuickFilterSelected("today")
        vm.onWheelchairToggle()
        assertEquals(3, vm.activeFilterCount())
    }

    private fun sampleEvent(id: String, bookmarked: Boolean) = EventListItemDto(
        id = id, host_id = "h", title = "t", description = null,
        start_datetime = "2026-06-01T10:00:00+00:00",
        end_datetime = "2026-06-01T12:00:00+00:00",
        visibility = "public", is_age_restricted = false,
        attendee_limit = null, attendee_count = 0, status = "published",
        is_bookmarked = bookmarked, attendance_status = null,
        going_count = 0, bookmark_count = 0, is_full = false,
        categories = emptyList(), primary_location = null, primary_image_url = null
    )
}
