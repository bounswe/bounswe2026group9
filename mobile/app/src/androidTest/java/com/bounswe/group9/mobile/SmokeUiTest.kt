package com.bounswe.group9.mobile

import androidx.compose.material3.Text
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test

/**
 * Smoke test for the Compose UI testing stack. We don't import a real screen
 * here on purpose — keeping the canary minimal means CI tells us when the
 * Compose test toolchain is broken, not when a feature changed copy.
 */
class SmokeUiTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun compose_renders_and_finds_text() {
        composeRule.setContent {
            Text("hello-from-compose-test")
        }

        composeRule.onNodeWithText("hello-from-compose-test").assertIsDisplayed()
    }
}
