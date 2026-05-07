package com.bounswe.group9.mobile.ui.notifications

import com.bounswe.group9.mobile.data.remote.NotificationDto
import com.bounswe.group9.mobile.data.remote.NotificationListResponseDto
import com.bounswe.group9.mobile.data.remote.NotificationReadAllResponseDto
import com.bounswe.group9.mobile.data.remote.NotificationReadResponseDto
import com.bounswe.group9.mobile.data.repository.NotificationRepository
import com.bounswe.group9.mobile.testing.MainDispatcherExtension
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.extension.ExtendWith

@OptIn(ExperimentalCoroutinesApi::class)
@ExtendWith(MainDispatcherExtension::class)
class NotificationViewModelTest {

    private val repository = mockk<NotificationRepository>()

    private fun viewModel() = NotificationViewModel(repository)

    @Test
    fun `setToken triggers initial load and surfaces unread count`() = runTest {
        coEvery { repository.getNotifications("tok", any()) } returns Result.success(
            NotificationListResponseDto(
                items = listOf(
                    notification("n1", read = false),
                    notification("n2", read = true)
                ),
                total = 2, unread_count = 1, page = 1, page_size = 20, total_pages = 1
            )
        )

        val vm = viewModel()
        vm.setToken("tok")
        advanceUntilIdle()

        assertEquals(2, vm.uiState.value.notifications.size)
        assertEquals(1, vm.uiState.value.unreadCount)
        coVerify { repository.getNotifications("tok", 1) }
    }

    @Test
    fun `setToken null clears state without calling the repo`() = runTest {
        coEvery { repository.getNotifications(any(), any()) } returns Result.success(emptyResponse())
        val vm = viewModel()
        vm.setToken("tok")
        advanceUntilIdle()

        vm.setToken(null)

        assertEquals(NotificationUiState(), vm.uiState.value)
        coVerify(exactly = 1) { repository.getNotifications(any(), any()) }
    }

    @Test
    fun `markAsRead flips item and decrements unreadCount`() = runTest {
        coEvery { repository.getNotifications("tok", any()) } returns Result.success(
            NotificationListResponseDto(
                items = listOf(
                    notification("n1", read = false),
                    notification("n2", read = false)
                ),
                total = 2, unread_count = 2, page = 1, page_size = 20, total_pages = 1
            )
        )
        coEvery { repository.markAsRead("tok", "n1") } returns Result.success(
            NotificationReadResponseDto(id = "n1", is_read = true)
        )

        val vm = viewModel()
        vm.setToken("tok")
        advanceUntilIdle()

        vm.markAsRead("n1")
        advanceUntilIdle()

        val state = vm.uiState.value
        assertTrue(state.notifications.first { it.id == "n1" }.is_read)
        assertEquals(1, state.unreadCount)
    }

    @Test
    fun `markAllAsRead flips every item and zeros the badge`() = runTest {
        coEvery { repository.getNotifications("tok", any()) } returns Result.success(
            NotificationListResponseDto(
                items = listOf(
                    notification("n1", read = false),
                    notification("n2", read = false)
                ),
                total = 2, unread_count = 2, page = 1, page_size = 20, total_pages = 1
            )
        )
        coEvery { repository.markAllAsRead("tok") } returns Result.success(
            NotificationReadAllResponseDto(updated_count = 2)
        )

        val vm = viewModel()
        vm.setToken("tok")
        advanceUntilIdle()

        vm.markAllAsRead()
        advanceUntilIdle()

        val state = vm.uiState.value
        assertTrue(state.notifications.all { it.is_read })
        assertEquals(0, state.unreadCount)
    }

    @Test
    fun `event_recommended notifications flow through the list unchanged`() = runTest {
        // The VM is type-agnostic — surfacing this test pins the contract that
        // the new event_recommended type from issue #275 isn't filtered out.
        coEvery { repository.getNotifications("tok", any()) } returns Result.success(
            NotificationListResponseDto(
                items = listOf(notification("n1", read = false, type = "event_recommended")),
                total = 1, unread_count = 1, page = 1, page_size = 20, total_pages = 1
            )
        )

        val vm = viewModel()
        vm.setToken("tok")
        advanceUntilIdle()

        assertEquals("event_recommended", vm.uiState.value.notifications.first().type)
    }

    private fun notification(id: String, read: Boolean, type: String = "event_updated") =
        NotificationDto(
            id = id,
            user_id = "u1",
            event_id = "e1",
            type = type,
            message = "m",
            is_read = read,
            created_at = "2026-01-01T00:00:00Z"
        )

    private fun emptyResponse() = NotificationListResponseDto(
        items = emptyList(),
        total = 0,
        unread_count = 0,
        page = 1,
        page_size = 20,
        total_pages = 1
    )
}
