package com.bounswe.group9.mobile.ui.discovery

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.bounswe.group9.mobile.data.repository.EventRepository
import io.mockk.coEvery
import io.mockk.mockk
import com.bounswe.group9.mobile.data.remote.EventListResponse
import org.junit.Rule
import org.junit.Test

/**
 * Compose UI tests for DiscoveryScreen — verifies key UI elements render
 * and the filter sheet opens correctly. Repository is mocked; no network.
 */
class DiscoveryScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun stubViewModel(): DiscoveryViewModel {
        val repo = mockk<EventRepository>(relaxed = true)
        coEvery { repo.getCategories() } returns Result.success(emptyList())
        coEvery {
            repo.getEvents(
                token = any(), search = any(), categoryId = any(), quickFilter = any(),
                wheelchair = any(), accessibleRestroom = any(), elevator = any(),
                seating = any(), captions = any(), quietFriendly = any(),
                sort = any(), nearLat = any(), nearLng = any(), radiusKm = any(),
                page = any(), pageSize = any()
            )
        } returns Result.success(
            EventListResponse(items = emptyList(), total = 0, page = 1, page_size = 20, total_pages = 1)
        )
        return DiscoveryViewModel(repo)
    }

    @Test
    fun discovery_screen_renders_search_bar_and_app_title() {
        composeRule.setContent {
            DiscoveryScreen(
                viewModel = stubViewModel(),
                token = null,
                onEventClick = {}
            )
        }

        composeRule.onNodeWithText("SOCIAL EVENT MAPPER").assertIsDisplayed()
        composeRule.onNodeWithText("Search events or places...").assertIsDisplayed()
    }

    @Test
    fun discovery_screen_shows_discover_tab_label() {
        composeRule.setContent {
            DiscoveryScreen(
                viewModel = stubViewModel(),
                token = null,
                onEventClick = {}
            )
        }

        composeRule.onNodeWithText("Discover").assertIsDisplayed()
    }

    @Test
    fun clicking_filter_button_opens_filter_sheet() {
        composeRule.setContent {
            DiscoveryScreen(
                viewModel = stubViewModel(),
                token = null,
                onEventClick = {}
            )
        }

        composeRule.onNodeWithContentDescription("Open Filters").performClick()
        composeRule.onNodeWithText("Filters").assertIsDisplayed()
        composeRule.onNodeWithText("Apply Filters").assertIsDisplayed()
    }

    @Test
    fun filter_sheet_shows_quick_filters_section() {
        composeRule.setContent {
            DiscoveryScreen(
                viewModel = stubViewModel(),
                token = null,
                onEventClick = {}
            )
        }

        composeRule.onNodeWithContentDescription("Open Filters").performClick()
        composeRule.onNodeWithText("QUICK FILTERS").assertIsDisplayed()
        composeRule.onNodeWithText("Today").assertIsDisplayed()
        composeRule.onNodeWithText("Weekend").assertIsDisplayed()
    }
}
