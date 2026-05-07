package com.bounswe.group9.mobile.data.remote

import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

/**
 * Pins the auth Retrofit/Gson contract: how login/register payloads are
 * serialised to JSON and how the AuthResponse is parsed back. Uses a fresh
 * `MockWebServer`-backed `ApiService` so this test never touches the
 * production `RetrofitProvider`.
 */
class AuthApiContractTest {

    private lateinit var server: MockWebServer
    private lateinit var api: ApiService

    @BeforeEach
    fun setUp() {
        server = MockWebServer()
        server.start()
        api = Retrofit.Builder()
            .baseUrl(server.url("/"))
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }

    @AfterEach
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun `login posts credentials JSON and parses AuthResponse`() = runTest {
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """
                {
                  "user":{"id":"u1","username":"alice","email":"a@b.com"},
                  "access_token":"tok",
                  "token_type":"bearer"
                }
                """.trimIndent()
            )
        )

        val response = api.login(LoginRequest("a@b.com", "secret"))

        assertEquals("tok", response.access_token)
        assertEquals("alice", response.user.username)

        val sent = server.takeRequest()
        assertEquals("/auth/login", sent.path)
        val body = sent.body.readUtf8()
        assertTrue(body.contains("\"email\":\"a@b.com\""), "body should carry email: $body")
        assertTrue(body.contains("\"password\":\"secret\""), "body should carry password: $body")
    }

    @Test
    fun `register serializes username email password and date_of_birth fields`() = runTest {
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """
                {
                  "user":{"id":"u1","username":"alice","email":"a@b.com"},
                  "access_token":"tok",
                  "token_type":"bearer"
                }
                """.trimIndent()
            )
        )

        api.register(RegisterRequest("alice", "a@b.com", "password123", "2000-01-01"))

        val sent = server.takeRequest()
        assertEquals("/auth/register", sent.path)
        val body = sent.body.readUtf8()
        assertTrue(body.contains("\"username\":\"alice\""))
        assertTrue(body.contains("\"email\":\"a@b.com\""))
        assertTrue(body.contains("\"password\":\"password123\""))
        assertTrue(body.contains("\"date_of_birth\":\"2000-01-01\""))
    }
}
