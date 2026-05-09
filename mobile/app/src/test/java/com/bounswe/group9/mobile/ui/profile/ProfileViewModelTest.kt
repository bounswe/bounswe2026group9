package com.bounswe.group9.mobile.ui.profile

import com.bounswe.group9.mobile.data.remote.BookmarkListResponseDto
import com.bounswe.group9.mobile.data.remote.EventListItemDto
import com.bounswe.group9.mobile.data.remote.HostProfileDto
import com.bounswe.group9.mobile.data.remote.MyProfileDto
import com.bounswe.group9.mobile.data.repository.ProfileRepository
import com.bounswe.group9.mobile.testing.MainDispatcherExtension
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.extension.ExtendWith

@OptIn(ExperimentalCoroutinesApi::class)
@ExtendWith(MainDispatcherExtension::class)
class ProfileViewModelTest {

    private val repository = mockk<ProfileRepository>()

    private fun stubAllLoads(rating: Double? = 4.5) {
        coEvery { repository.getMe(any()) } returns Result.success(
            MyProfileDto(id = "u1", username = "alice", email = "a@b.com")
        )
        coEvery { repository.getHostProfile(any(), any()) } returns Result.success(
            HostProfileDto(
                id = "u1", username = "alice", email = null, phone_number = null,
                average_rating = rating, hosted_events_count = 0, hosted_events = emptyList()
            )
        )
        coEvery { repository.getBookmarks(any(), any(), any()) } returns Result.success(
            BookmarkListResponseDto(
                items = emptyList(), total = 0, page = 1, page_size = 20, total_pages = 1
            )
        )
        coEvery { repository.getMyGoingEvents(any()) } returns Result.success(
            emptyList<EventListItemDto>()
        )
    }

    @Test
    fun `setCredentials with token and id triggers profile + hosted + bookmarks fetch`() = runTest {
        stubAllLoads()
        val vm = ProfileViewModel(repository)

        vm.setCredentials("tok", "u1")
        advanceUntilIdle()

        coVerify { repository.getMe("tok") }
        coVerify { repository.getHostProfile("tok", "u1") }
        coVerify { repository.getBookmarks("tok", any(), any()) }
        assertEquals(4.5, vm.uiState.value.averageRating)
    }

    @Test
    fun `setCredentials with null clears profile state`() = runTest {
        stubAllLoads()
        val vm = ProfileViewModel(repository)
        vm.setCredentials("tok", "u1")
        advanceUntilIdle()

        vm.setCredentials(null, null)
        advanceUntilIdle()

        assertEquals(ProfileUiState(), vm.uiState.value)
    }

    @Test
    fun `saveProfile success surfaces successMessage and clears isSaving`() = runTest {
        stubAllLoads()
        coEvery { repository.updateProfile(any(), any()) } returns Result.success(
            MyProfileDto(
                id = "u1", username = "alice", email = "a@b.com",
                phone_number = "+90", date_of_birth = "2000-01-01"
            )
        )
        val vm = ProfileViewModel(repository)
        vm.setCredentials("tok", "u1")
        advanceUntilIdle()
        vm.onPhoneChange("+90")

        vm.saveProfile()
        advanceUntilIdle()

        assertEquals("Profile updated successfully", vm.uiState.value.successMessage)
        assertFalse(vm.uiState.value.isSaving)
    }

    @Test
    fun `saveProfile failure surfaces errorMessage and clears isSaving`() = runTest {
        stubAllLoads()
        coEvery { repository.updateProfile(any(), any()) } returns Result.failure(Exception("boom"))
        val vm = ProfileViewModel(repository)
        vm.setCredentials("tok", "u1")
        advanceUntilIdle()

        vm.saveProfile()
        advanceUntilIdle()

        assertEquals("boom", vm.uiState.value.errorMessage)
        assertFalse(vm.uiState.value.isSaving)
    }
}
