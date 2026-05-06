package com.bounswe.group9.mobile.data.remote

import com.bounswe.group9.mobile.data.repository.NotificationRepository
import io.mockk.every
import io.mockk.mockkObject
import io.mockk.unmockkObject
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
 * End-to-end contract tests for the notifications API path. We swap
 * `RetrofitProvider.apiService` for a fresh ApiService bound to MockWebServer
 * so the full Retrofit/OkHttp/Gson pipeline is exercised — header injection,
 * pagination query params, and Result-wrapped failure mapping on 5xx.
 */
class NotificationApiContractTest {

    private lateinit var server: MockWebServer
    private lateinit var realApi: ApiService
    private lateinit var repository: NotificationRepository

    @BeforeEach
    fun setUp() {
        server = MockWebServer()
        server.start()
        realApi = Retrofit.Builder()
            .baseUrl(server.url("/"))
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
        mockkObject(RetrofitProvider)
        every { RetrofitProvider.apiService } returns realApi
        repository = NotificationRepository()
    }

    @AfterEach
    fun tearDown() {
        unmockkObject(RetrofitProvider)
        server.shutdown()
    }

    @Test
    fun `getNotifications encodes paging and sends bearer header`() = runTest {
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """{"items":[],"total":0,"unread_count":0,"page":3,"page_size":20,"total_pages":3}"""
            )
        )

        val result = repository.getNotifications(token = "tok", page = 3)

        assertTrue(result.isSuccess)
        val sent = server.takeRequest()
        assertEquals("/notifications", sent.requestUrl!!.encodedPath)
        assertEquals("3", sent.requestUrl!!.queryParameter("page"))
        assertEquals("20", sent.requestUrl!!.queryParameter("page_size"))
        assertEquals("Bearer tok", sent.getHeader("Authorization"))
    }

    @Test
    fun `getNotifications wraps a 5xx response in Result failure`() = runTest {
        server.enqueue(MockResponse().setResponseCode(500).setBody("""{"detail":"boom"}"""))

        val result = repository.getNotifications(token = "tok")

        assertTrue(result.isFailure)
    }
}
