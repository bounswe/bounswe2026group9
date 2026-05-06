package com.bounswe.group9.mobile.data.repository

import com.bounswe.group9.mobile.data.remote.ApiService
import com.bounswe.group9.mobile.data.remote.RetrofitProvider
import io.mockk.every
import io.mockk.mockkObject
import io.mockk.unmockkObject
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

/**
 * End-to-end repository tests against [MockWebServer]. We swap
 * `RetrofitProvider.apiService` for a fresh ApiService pointed at the mock
 * server so the full Retrofit/OkHttp/Gson pipeline (header injection, query
 * encoding, response parsing) is exercised — not a mock at every layer.
 */
class EventRepositoryTest {

    private lateinit var server: MockWebServer
    private lateinit var realApi: ApiService
    private lateinit var repository: EventRepository

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
        repository = EventRepository()
    }

    @AfterEach
    fun tearDown() {
        unmockkObject(RetrofitProvider)
        server.shutdown()
    }

    private companion object {
        const val EMPTY_EVENTS_BODY =
            """{"items":[],"total":0,"page":1,"page_size":20,"total_pages":1}"""
    }

    @Test
    fun `getEvents serialises every filter as a query parameter and adds bearer header`() = runTest {
        server.enqueue(MockResponse().setResponseCode(200).setBody(EMPTY_EVENTS_BODY))

        repository.getEvents(
            token = "tok",
            search = "jazz",
            categoryId = "cat-1",
            quickFilter = "weekend",
            wheelchair = true,
            sort = "distance",
            nearLat = 41.0,
            nearLng = 29.0,
            radiusKm = 5.0,
            page = 2
        )

        val sent = server.takeRequest()
        assertEquals("Bearer tok", sent.getHeader("Authorization"))
        val url = sent.requestUrl!!
        assertEquals("/events", url.encodedPath)
        assertEquals("jazz", url.queryParameter("search"))
        assertEquals("cat-1", url.queryParameter("category_id"))
        assertEquals("weekend", url.queryParameter("quick_filter"))
        assertEquals("true", url.queryParameter("wheelchair"))
        assertEquals("41.0", url.queryParameter("near_lat"))
        assertEquals("29.0", url.queryParameter("near_lng"))
        assertEquals("5.0", url.queryParameter("radius_km"))
        assertEquals("distance", url.queryParameter("sort"))
        assertEquals("2", url.queryParameter("page"))
    }

    @Test
    fun `getEvents drops blank search to avoid sending an empty query`() = runTest {
        server.enqueue(MockResponse().setResponseCode(200).setBody(EMPTY_EVENTS_BODY))

        repository.getEvents(token = null, search = "   ")

        val sent = server.takeRequest()
        // Repository's `search?.takeIf { it.isNotBlank() }` should result in no `search=`.
        assertNull(sent.requestUrl!!.queryParameter("search"))
    }

    @Test
    fun `getEvents 401 retries the request without the Authorization header`() = runTest {
        server.enqueue(MockResponse().setResponseCode(401))
        server.enqueue(MockResponse().setResponseCode(200).setBody(EMPTY_EVENTS_BODY))

        val result = repository.getEvents(token = "stale")

        assertTrue(result.isSuccess)
        val first = server.takeRequest()
        val second = server.takeRequest()
        assertEquals("Bearer stale", first.getHeader("Authorization"))
        assertNull(second.getHeader("Authorization"))
    }

    @Test
    fun `addBookmark POSTs to events bookmark path with bearer header`() = runTest {
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """{"id":"b1","event_id":"e1","created_at":"2026-01-01T00:00:00Z"}"""
            )
        )

        val result = repository.addBookmark("tok", "e1")

        assertTrue(result.isSuccess)
        val sent = server.takeRequest()
        assertEquals("/events/e1/bookmark", sent.path)
        assertEquals("POST", sent.method)
        assertEquals("Bearer tok", sent.getHeader("Authorization"))
    }
}
