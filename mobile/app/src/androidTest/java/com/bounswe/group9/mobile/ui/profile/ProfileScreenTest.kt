package com.bounswe.group9.mobile.ui.profile

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import com.bounswe.group9.mobile.data.repository.ProfileRepository
import io.mockk.coEvery
import io.mockk.mockk
import com.bounswe.group9.mobile.data.remote.EventListItemDto
import org.junit.Rule
import org.junit.Test

/**
 * Compose UI tests for ProfileScreen. Verifies that the profile header,
 * stat cards, and top bar render correctly. Repository is mocked; no network.
 */
class ProfileScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun stubViewModel(): ProfileViewModel {
        val repo = mockk<ProfileRepository>(relaxed = true)
        coEvery { repo.getMyGoingEvents(any()) } returns Result.success(emptyList())
        return ProfileViewModel(repo)
    }

    @Test
    fun profile_screen_shows_my_profile_title() {
        composeRule.setContent {
            ProfileScreen(
                viewModel = stubViewModel(),
                token = "tok",
                username = "testuser",
                onBack = {},
                onEventClick = {}
            )
        }

        composeRule.onNodeWithText("My Profile").assertIsDisplayed()
    }

    @Test
    fun profile_screen_shows_username_in_header() {
        composeRule.setContent {
            ProfileScreen(
                viewModel = stubViewModel(),
                token = "tok",
                username = "testuser",
                onBack = {},
                onEventClick = {}
            )
        }

        composeRule.onNodeWithText("testuser").assertIsDisplayed()
    }

    @Test
    fun profile_screen_shows_stat_cards() {
        composeRule.setContent {
            ProfileScreen(
                viewModel = stubViewModel(),
                token = "tok",
                username = "testuser",
                onBack = {},
                onEventClick = {}
            )
        }

        composeRule.onNodeWithText("EVENTS").assertIsDisplayed()
        composeRule.onNodeWithText("AVG RATING").assertIsDisplayed()
        composeRule.onNodeWithText("UPCOMING").assertIsDisplayed()
    }
}
