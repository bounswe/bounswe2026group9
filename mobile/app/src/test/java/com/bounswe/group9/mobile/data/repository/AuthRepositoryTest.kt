package com.bounswe.group9.mobile.data.repository

import com.bounswe.group9.mobile.data.remote.ApiService
import com.bounswe.group9.mobile.data.remote.AuthResponse
import com.bounswe.group9.mobile.data.remote.RetrofitProvider
import com.bounswe.group9.mobile.data.remote.UserResponse
import io.mockk.coEvery
import io.mockk.every
import io.mockk.mockk
import io.mockk.mockkObject
import io.mockk.unmockkObject
import kotlinx.coroutines.test.runTest
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import retrofit2.HttpException
import retrofit2.Response

/**
 * Verifies the friendly-message mapping in [AuthRepository] without needing a real
 * network — `RetrofitProvider.apiService` is swapped via `mockkObject` so the
 * repository's hardcoded singleton dependency stays internal to the production code.
 */
class AuthRepositoryTest {

    private val mockApi = mockk<ApiService>()
    private val repository = AuthRepository()

    @BeforeEach
    fun stubApi() {
        mockkObject(RetrofitProvider)
        every { RetrofitProvider.apiService } returns mockApi
    }

    @AfterEach
    fun unstubApi() {
        unmockkObject(RetrofitProvider)
    }

    private fun httpError(code: Int, jsonBody: String): HttpException = HttpException(
        Response.error<AuthResponse>(
            code,
            jsonBody.toResponseBody("application/json".toMediaType())
        )
    )

    @Test
    fun `login wraps a 200 AuthResponse in Result success`() = runTest {
        coEvery { mockApi.login(any()) } returns AuthResponse(
            user = UserResponse("u1", "alice", "a@b.com"),
            access_token = "abc",
            token_type = "bearer"
        )

        val result = repository.login("a@b.com", "secret")

        assertTrue(result.isSuccess)
        val auth = result.getOrThrow()
        assertEquals("abc", auth.accessToken)
        assertEquals("alice", auth.user.username)
    }

    @Test
    fun `login 401 maps to invalid-credentials friendly message`() = runTest {
        coEvery { mockApi.login(any()) } throws httpError(401, "{}")

        val result = repository.login("a@b.com", "wrong")

        assertTrue(result.isFailure)
        assertEquals("Incorrect email or password.", result.exceptionOrNull()?.message)
    }

    @Test
    fun `login 422 with detail field surfaces server-supplied text`() = runTest {
        coEvery { mockApi.login(any()) } throws httpError(
            422,
            """{"detail":"Email already taken."}"""
        )

        val result = repository.login("a@b.com", "secret")

        assertTrue(result.isFailure)
        assertEquals("Email already taken.", result.exceptionOrNull()?.message)
    }

    @Test
    fun `register 409 maps to duplicate-account friendly message`() = runTest {
        coEvery { mockApi.register(any()) } throws httpError(409, "{}")

        val result = repository.register("alice", "a@b.com", "password123", "2000-01-01")

        assertTrue(result.isFailure)
        assertEquals(
            "An account with this email or username already exists.",
            result.exceptionOrNull()?.message
        )
    }
}
