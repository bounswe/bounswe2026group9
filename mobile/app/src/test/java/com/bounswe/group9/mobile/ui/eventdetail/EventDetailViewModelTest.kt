package com.bounswe.group9.mobile.ui.eventdetail

import com.bounswe.group9.mobile.data.remote.AccessRequestListResponseDto
import com.bounswe.group9.mobile.data.remote.AccessRequestResponseDto
import com.bounswe.group9.mobile.data.remote.CommentAuthorDto
import com.bounswe.group9.mobile.data.remote.CommentDto
import com.bounswe.group9.mobile.data.remote.CommentListResponseDto
import com.bounswe.group9.mobile.data.remote.EventDetailDto
import com.bounswe.group9.mobile.data.remote.EventLimitedDto
import com.bounswe.group9.mobile.data.remote.HostProfileDto
import com.bounswe.group9.mobile.data.remote.InviteListResponseDto
import com.bounswe.group9.mobile.data.repository.EventDetailError
import com.bounswe.group9.mobile.data.repository.EventDetailResult
import com.bounswe.group9.mobile.data.repository.EventRepository
import com.bounswe.group9.mobile.data.repository.ProfileRepository
import com.bounswe.group9.mobile.testing.MainDispatcherExtension
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.extension.ExtendWith

@OptIn(ExperimentalCoroutinesApi::class)
@ExtendWith(MainDispatcherExtension::class)
class EventDetailViewModelTest {

    private val repository = mockk<EventRepository>()
    private val profileRepository = mockk<ProfileRepository>()

    @BeforeEach
    fun stubAmbientLoads() {
        // The VM fires a fan-out of secondary loads (comments, invites, similar
        // events, host name) every time loadEvent succeeds. Stub them once so
        // each test only has to focus on the interaction it cares about.
        coEvery { repository.getComments(any(), any()) } returns Result.success(emptyComments())
        coEvery { repository.getSimilarEvents(any(), any()) } returns Result.success(emptyList())
        coEvery { repository.listInvites(any(), any()) } returns Result.success(InviteListResponseDto(emptyList()))
        coEvery { repository.listAccessRequests(any(), any()) } returns Result.success(
            AccessRequestListResponseDto(emptyList())
        )
        coEvery { profileRepository.getHostProfile(any(), any()) } returns Result.success(sampleHost())
    }

    private fun viewModel() = EventDetailViewModel(repository, profileRepository)

    @Test
    fun `loadEvent full result populates fullDetail`() = runTest {
        coEvery { repository.getEventDetail(any(), "e1") } returns Result.success(
            EventDetailResult.Full(fullEvent(id = "e1"))
        )

        val vm = viewModel()
        vm.loadEvent("e1", "tok")
        advanceUntilIdle()

        assertEquals("e1", vm.uiState.value.fullDetail?.id)
        assertNull(vm.uiState.value.detailError)
    }

    @Test
    fun `loadEvent limited result populates limitedPreview`() = runTest {
        coEvery { repository.getEventDetail(any(), "e1") } returns Result.success(
            EventDetailResult.Limited(limitedPreview())
        )

        val vm = viewModel()
        vm.loadEvent("e1", null)
        advanceUntilIdle()

        assertEquals("e1", vm.uiState.value.limitedPreview?.id)
        assertNull(vm.uiState.value.fullDetail)
    }

    @Test
    fun `loadEvent NotFound failure surfaces typed detailError`() = runTest {
        coEvery { repository.getEventDetail(any(), "e1") } returns Result.failure(
            EventDetailError.NotFound()
        )

        val vm = viewModel()
        vm.loadEvent("e1", null)
        advanceUntilIdle()

        assertTrue(vm.uiState.value.detailError is EventDetailError.NotFound)
    }

    @Test
    fun `setGoing optimistically increments going_count and flips status`() = runTest {
        coEvery { repository.getEventDetail(any(), "e1") } returns Result.success(
            EventDetailResult.Full(fullEvent(id = "e1", attendanceStatus = null, goingCount = 5))
        )
        coEvery { repository.setAttendance("tok", "e1", "going") } returns Result.success(Unit)

        val vm = viewModel()
        vm.loadEvent("e1", "tok")
        advanceUntilIdle()

        vm.setGoing()
        advanceUntilIdle()

        assertEquals("going", vm.uiState.value.fullDetail?.attendance_status)
        assertEquals(6, vm.uiState.value.fullDetail?.going_count)
        assertNull(vm.uiState.value.actionError)
    }

    @Test
    fun `setGoing rolls back state and surfaces actionError on failure`() = runTest {
        coEvery { repository.getEventDetail(any(), "e1") } returns Result.success(
            EventDetailResult.Full(fullEvent(id = "e1", attendanceStatus = null, goingCount = 5))
        )
        coEvery { repository.setAttendance(any(), any(), any()) } returns Result.failure(Exception("boom"))

        val vm = viewModel()
        vm.loadEvent("e1", "tok")
        advanceUntilIdle()

        vm.setGoing()
        advanceUntilIdle()

        assertNull(vm.uiState.value.fullDetail?.attendance_status)
        assertEquals(5, vm.uiState.value.fullDetail?.going_count)
        assertEquals("boom", vm.uiState.value.actionError)
    }

    @Test
    fun `removeAttendance decrements going count and clears status`() = runTest {
        coEvery { repository.getEventDetail(any(), "e1") } returns Result.success(
            EventDetailResult.Full(fullEvent(id = "e1", attendanceStatus = "going", goingCount = 5))
        )
        coEvery { repository.removeAttendance("tok", "e1") } returns Result.success(Unit)

        val vm = viewModel()
        vm.loadEvent("e1", "tok")
        advanceUntilIdle()

        vm.removeAttendance()
        advanceUntilIdle()

        assertNull(vm.uiState.value.fullDetail?.attendance_status)
        assertEquals(4, vm.uiState.value.fullDetail?.going_count)
    }

    @Test
    fun `toggleBookmark optimistic flip rolls back on failure`() = runTest {
        coEvery { repository.getEventDetail(any(), "e1") } returns Result.success(
            EventDetailResult.Full(fullEvent(id = "e1", isBookmarked = false))
        )
        coEvery { repository.addBookmark("tok", "e1") } returns Result.failure(Exception("nope"))

        val vm = viewModel()
        vm.loadEvent("e1", "tok")
        advanceUntilIdle()

        vm.toggleBookmark()
        advanceUntilIdle()

        assertEquals(false, vm.uiState.value.fullDetail?.is_bookmarked)
        assertEquals("nope", vm.uiState.value.actionError)
    }

    @Test
    fun `postComment success prepends new comment and clears the input`() = runTest {
        coEvery { repository.getEventDetail(any(), "e1") } returns Result.success(
            EventDetailResult.Full(fullEvent(id = "e1"))
        )
        val newComment = CommentDto(
            id = "c1", event_id = "e1",
            user = CommentAuthorDto("u1", "alice"),
            text = "hi", created_at = "2026-01-01T00:00:00Z"
        )
        coEvery { repository.postComment("tok", "e1", "hi") } returns Result.success(newComment)

        val vm = viewModel()
        vm.loadEvent("e1", "tok")
        advanceUntilIdle()
        vm.onCommentTextChange("hi")

        vm.postComment()
        advanceUntilIdle()

        assertEquals("c1", vm.uiState.value.comments.firstOrNull()?.id)
        assertEquals("", vm.uiState.value.commentText)
    }

    @Test
    fun `requestAccess success updates accessRequestStatus`() = runTest {
        coEvery { repository.getEventDetail(any(), "e1") } returns Result.success(
            EventDetailResult.Limited(limitedPreview())
        )
        coEvery { repository.requestAccess("tok", "e1") } returns Result.success(
            AccessRequestResponseDto(
                id = "r1", event_id = "e1", user_id = "u1", username = "alice",
                status = "pending", created_at = "2026-01-01T00:00:00Z", resolved_at = null
            )
        )

        val vm = viewModel()
        vm.loadEvent("e1", "tok")
        advanceUntilIdle()

        vm.requestAccess()
        advanceUntilIdle()

        assertEquals("pending", vm.uiState.value.accessRequestStatus)
    }

    // ── helpers ──────────────────────────────────────────────────────────────

    private fun fullEvent(
        id: String = "e1",
        attendanceStatus: String? = null,
        isBookmarked: Boolean? = null,
        goingCount: Int = 0,
        attendeeLimit: Int? = null
    ) = EventDetailDto(
        id = id, host_id = "host-1", host_username = null,
        title = "Title", description = "Desc",
        start_datetime = "2026-06-01T10:00:00+00:00",
        end_datetime = "2026-06-01T12:00:00+00:00",
        visibility = "public", is_age_restricted = false,
        attendee_limit = attendeeLimit, attendee_count = goingCount,
        status = "published",
        created_at = "2026-01-01T00:00:00Z",
        updated_at = "2026-01-01T00:00:00Z",
        is_bookmarked = isBookmarked,
        attendance_status = attendanceStatus,
        going_count = goingCount, bookmark_count = 0,
        is_full = attendeeLimit != null && goingCount >= attendeeLimit,
        locations = emptyList(), categories = emptyList(),
        images = emptyList(), venue_metadata = null,
        equipment_requirements = emptyList(), segments = null
    )

    private fun limitedPreview() = EventLimitedDto(
        id = "e1", title = "Private Event",
        start_datetime = "2026-06-01T10:00:00+00:00",
        end_datetime = "2026-06-01T12:00:00+00:00",
        visibility = "private", is_age_restricted = false,
        status = "published", is_bookmarked = null,
        access_request_status = null, categories = emptyList()
    )

    private fun emptyComments() = CommentListResponseDto(
        items = emptyList(), total = 0, page = 1, page_size = 20, total_pages = 1
    )

    private fun sampleHost() = HostProfileDto(
        id = "host-1", username = "host-name", email = null, phone_number = null,
        average_rating = null, hosted_events_count = 0, hosted_events = emptyList()
    )
}
