package com.bounswe.group9.mobile.ui.auth

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.bounswe.group9.mobile.data.local.SessionManager
import com.bounswe.group9.mobile.data.repository.AuthRepository
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.flow.flowOf
import org.junit.Rule
import org.junit.Test

/**
 * Compose UI smoke tests for the Login/Register tabbed screen. Asserts the
 * tabbed title swap, register-only field visibility, and the validation flow
 * surfaced by the underlying [AuthViewModel] (no network — repository is mocked).
 */
class LoginScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    private fun viewModel(): AuthViewModel {
        val sessionManager = mockk<SessionManager>(relaxed = true)
        every { sessionManager.tokenFlow } returns flowOf(null)
        every { sessionManager.usernameFlow } returns flowOf(null)
        return AuthViewModel(repository = mockk<AuthRepository>(relaxed = true), sessionManager = sessionManager)
    }

    @Test
    fun login_tab_renders_welcome_back_title_by_default() {
        composeRule.setContent { LoginScreen(viewModel = viewModel()) }

        composeRule.onNodeWithText("Welcome back").assertIsDisplayed()
        composeRule.onNodeWithText("Sign in to your account").assertIsDisplayed()
    }

    @Test
    fun clicking_sign_up_tab_switches_to_register_view() {
        composeRule.setContent { LoginScreen(viewModel = viewModel()) }

        composeRule.onNodeWithText("Sign Up").performClick()

        composeRule.onNodeWithText("Create account").assertIsDisplayed()
        // Username field is register-only and only renders after the tab switch.
        composeRule.onNodeWithText("Username").assertIsDisplayed()
        composeRule.onNodeWithText("Date of Birth").assertIsDisplayed()
    }

    @Test
    fun submitting_login_with_blank_fields_shows_validation_error() {
        val vm = viewModel()
        composeRule.setContent { LoginScreen(viewModel = vm) }

        // Trigger the VM's blank-input branch directly so we don't fight the
        // ambiguous "Sign In" text (it doubles as a tab and the primary button).
        composeRule.runOnIdle { vm.login() }

        composeRule.onNodeWithText("Email is required.").assertIsDisplayed()
    }
}
