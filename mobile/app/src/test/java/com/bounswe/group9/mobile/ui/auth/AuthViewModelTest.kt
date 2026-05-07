package com.bounswe.group9.mobile.ui.auth

import com.bounswe.group9.mobile.data.local.SessionManager
import com.bounswe.group9.mobile.data.remote.UserResponse
import com.bounswe.group9.mobile.data.repository.AuthRepository
import com.bounswe.group9.mobile.data.repository.AuthResult
import com.bounswe.group9.mobile.testing.MainDispatcherExtension
import io.mockk.Runs
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.just
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flowOf
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
class AuthViewModelTest {

    private val repository = mockk<AuthRepository>()
    private val sessionManager = mockk<SessionManager>(relaxed = true)

    @BeforeEach
    fun stubSession() {
        every { sessionManager.tokenFlow } returns flowOf(null)
        every { sessionManager.usernameFlow } returns flowOf(null)
        coEvery { sessionManager.saveToken(any()) } just Runs
        coEvery { sessionManager.saveUsername(any()) } just Runs
        coEvery { sessionManager.saveUserId(any()) } just Runs
        coEvery { sessionManager.clearAll() } just Runs
        coEvery { sessionManager.getRefreshToken() } returns null
    }

    private fun viewModel() = AuthViewModel(repository, sessionManager)

    @Test
    fun `login with blank email surfaces validation error`() {
        val vm = viewModel()
        vm.onPasswordChange("password123")

        vm.login()

        assertEquals("Email is required.", vm.uiState.value.errorMessage)
        assertFalse(vm.uiState.value.isLoading)
    }

    @Test
    fun `login with blank password surfaces validation error`() {
        val vm = viewModel()
        vm.onEmailChange("a@b.com")

        vm.login()

        assertEquals("Password is required.", vm.uiState.value.errorMessage)
    }

    @Test
    fun `login success persists session and flips loggedIn`() = runTest {
        coEvery { repository.login("a@b.com", "secret") } returns Result.success(
            AuthResult("access-123", UserResponse("u1", "alice", "a@b.com"))
        )
        val vm = viewModel()
        vm.onEmailChange("a@b.com")
        vm.onPasswordChange("secret")

        vm.login()
        advanceUntilIdle()

        val state = vm.uiState.value
        assertTrue(state.isLoggedIn)
        assertEquals("alice", state.username)
        assertFalse(state.isLoading)
        assertNull(state.errorMessage)
        coVerify { sessionManager.saveToken("access-123") }
        coVerify { sessionManager.saveUsername("alice") }
        coVerify { sessionManager.saveUserId("u1") }
    }

    @Test
    fun `login failure surfaces error and stops loading`() = runTest {
        coEvery { repository.login(any(), any()) } returns Result.failure(
            Exception("Incorrect email or password.")
        )
        val vm = viewModel()
        vm.onEmailChange("a@b.com")
        vm.onPasswordChange("wrong")

        vm.login()
        advanceUntilIdle()

        val state = vm.uiState.value
        assertFalse(state.isLoggedIn)
        assertFalse(state.isLoading)
        assertEquals("Incorrect email or password.", state.errorMessage)
    }

    @Test
    fun `register rejects username shorter than three chars`() {
        val vm = viewModel()
        vm.onUsernameChange("ab")
        vm.onEmailChange("a@b.com")
        vm.onPasswordChange("password123")
        vm.onDateOfBirthChange("2000-01-01")

        vm.register()

        assertEquals("Username must be at least 3 characters.", vm.uiState.value.errorMessage)
    }

    @Test
    fun `register rejects password shorter than eight chars`() {
        val vm = viewModel()
        vm.onUsernameChange("alice")
        vm.onEmailChange("a@b.com")
        vm.onPasswordChange("short")
        vm.onDateOfBirthChange("2000-01-01")

        vm.register()

        assertEquals("Password must be at least 8 characters.", vm.uiState.value.errorMessage)
    }

    @Test
    fun `register rejects malformed date of birth`() {
        val vm = viewModel()
        vm.onUsernameChange("alice")
        vm.onEmailChange("a@b.com")
        vm.onPasswordChange("password123")
        vm.onDateOfBirthChange("01-01-2000")

        vm.register()

        assertEquals("Date of birth must be in YYYY-MM-DD format.", vm.uiState.value.errorMessage)
    }

    @Test
    fun `refreshSession failure forces logout and invokes onExpired`() = runTest {
        coEvery { repository.refreshToken(any()) } returns Result.failure(Exception("expired"))
        val vm = viewModel()
        var expiredCalled = false

        vm.refreshSession(onExpired = { expiredCalled = true })
        advanceUntilIdle()

        assertTrue(expiredCalled)
        assertFalse(vm.uiState.value.isLoggedIn)
        coVerify { sessionManager.clearAll() }
    }

    @Test
    fun `existing token in session flow flips isLoggedIn on init`() = runTest {
        // Cold-start "session restore on relaunch": SessionManager already has
        // a stored token, so AuthViewModel.init's tokenFlow collector should
        // bring the user back to a logged-in state without prompting login.
        every { sessionManager.tokenFlow } returns flowOf("existing-tok")
        every { sessionManager.usernameFlow } returns flowOf("alice")

        val vm = viewModel()
        advanceUntilIdle()

        assertTrue(vm.uiState.value.isLoggedIn)
        assertEquals("alice", vm.uiState.value.username)
    }

    @Test
    fun `refreshSession success persists rotated token and stays loggedIn`() = runTest {
        coEvery { repository.refreshToken(any()) } returns Result.success(
            AuthResult("fresh-token", UserResponse("u1", "alice", "a@b.com"))
        )
        val vm = viewModel()

        vm.refreshSession()
        advanceUntilIdle()

        assertTrue(vm.uiState.value.isLoggedIn)
        assertEquals("alice", vm.uiState.value.username)
        coVerify { sessionManager.saveToken("fresh-token") }
        coVerify { sessionManager.saveUserId("u1") }
    }

    @Test
    fun `logout clears session and resets ui state`() = runTest {
        val vm = viewModel()
        vm.onEmailChange("a@b.com")
        vm.onPasswordChange("secret")

        vm.logout()
        advanceUntilIdle()

        coVerify { sessionManager.clearAll() }
        assertEquals(AuthUiState(), vm.uiState.value)
    }
}
