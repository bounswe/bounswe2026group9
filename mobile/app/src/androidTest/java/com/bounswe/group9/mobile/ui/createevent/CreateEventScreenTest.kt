package com.bounswe.group9.mobile.ui.createevent

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test

/**
 * Compose UI tests for CreateEventScreen. Verifies that the form renders
 * correctly for authenticated and unauthenticated states. No network — uses
 * the default CreateEventViewModel with no token.
 */
class CreateEventScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun unauthenticated_shows_sign_in_required_message() {
        composeRule.setContent {
            CreateEventScreen(
                token = null,
                onBack = {},
                onEventSaved = {}
            )
        }

        composeRule.onNodeWithText("Sign in required").assertIsDisplayed()
        composeRule.onNodeWithText("You must be signed in to create or edit events.").assertIsDisplayed()
    }

    @Test
    fun authenticated_shows_event_title_field() {
        composeRule.setContent {
            CreateEventScreen(
                token = "fake-token",
                onBack = {},
                onEventSaved = {}
            )
        }

        composeRule.onNodeWithText("Event title").assertIsDisplayed()
        composeRule.onNodeWithText("Give your event a memorable name").assertIsDisplayed()
    }

    @Test
    fun authenticated_shows_next_and_back_navigation_buttons() {
        composeRule.setContent {
            CreateEventScreen(
                token = "fake-token",
                onBack = {},
                onEventSaved = {}
            )
        }

        composeRule.onNodeWithText("Next").assertIsDisplayed()
        composeRule.onNodeWithText("Back").assertIsDisplayed()
    }

    @Test
    fun authenticated_shows_save_draft_button() {
        composeRule.setContent {
            CreateEventScreen(
                token = "fake-token",
                onBack = {},
                onEventSaved = {}
            )
        }

        composeRule.onNodeWithText("Save draft").assertIsDisplayed()
    }
}
