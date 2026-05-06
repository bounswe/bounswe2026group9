package com.bounswe.group9.mobile.ui.createevent

import com.bounswe.group9.mobile.data.remote.CategoryDto
import com.bounswe.group9.mobile.data.repository.EventRepository
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
class CreateEventViewModelTest {

    private val repository = mockk<EventRepository>()

    @BeforeEach
    fun stub() {
        coEvery { repository.getCategories() } returns Result.success(emptyList())
    }

    private fun viewModel() = CreateEventViewModel(repository)

    @Test
    fun `init with null token surfaces a sign-in error`() {
        val vm = viewModel()
        vm.init(token = null)

        assertEquals(
            "You must be signed in to create or edit events.",
            vm.uiState.value.submitError
        )
    }

    @Test
    fun `init with token loads available categories`() = runTest {
        coEvery { repository.getCategories() } returns Result.success(
            listOf(CategoryDto("c1", "Music", is_predefined = true, is_approved = true))
        )

        val vm = viewModel()
        vm.init(token = "tok")
        advanceUntilIdle()

        assertEquals(1, vm.uiState.value.availableCategories.size)
        assertEquals("Music", vm.uiState.value.availableCategories.first().name)
    }

    @Test
    fun `nextStep on step 0 with blank fields sets per-field errors and stays on step 0`() {
        val vm = viewModel()

        vm.nextStep()

        val state = vm.uiState.value
        assertEquals(0, state.currentStep)
        assertEquals("Title is required", state.titleError)
        assertEquals("Description is required", state.descriptionError)
        assertEquals("Select at least one category", state.categoryError)
    }

    @Test
    fun `nextStep on step 0 with a complete form advances to step 1`() {
        val vm = viewModel()
        vm.onTitleChange("Concert")
        vm.onDescriptionChange("Best night ever")
        vm.toggleCategory("c1")

        vm.nextStep()

        assertEquals(1, vm.uiState.value.currentStep)
        assertNull(vm.uiState.value.titleError)
    }

    @Test
    fun `step 1 validation rejects end before start`() {
        val vm = viewModel()
        vm.onTitleChange("X"); vm.onDescriptionChange("X"); vm.toggleCategory("c1")
        vm.nextStep()  // → step 1
        assertEquals(1, vm.uiState.value.currentStep)

        vm.onStartDateChange("2026-06-01")
        vm.onStartTimeChange("12:00")
        vm.onEndDateChange("2026-06-01")
        vm.onEndTimeChange("11:00")  // before start

        vm.nextStep()

        assertEquals("End time must be after start time", vm.uiState.value.endError)
        assertEquals(1, vm.uiState.value.currentStep)
    }

    @Test
    fun `toggleCategory adds and removes ids from the set`() {
        val vm = viewModel()

        vm.toggleCategory("c1")
        assertEquals(setOf("c1"), vm.uiState.value.selectedCategoryIds)

        vm.toggleCategory("c2")
        assertEquals(setOf("c1", "c2"), vm.uiState.value.selectedCategoryIds)

        vm.toggleCategory("c1")
        assertEquals(setOf("c2"), vm.uiState.value.selectedCategoryIds)
    }

    @Test
    fun `onAttendeeLimitChange filters to digits only`() {
        val vm = viewModel()

        vm.onAttendeeLimitChange("12abc34")

        assertEquals("1234", vm.uiState.value.attendeeLimit)
    }

    @Test
    fun `addLocation appends and removeLocation respects the minimum of one`() {
        val vm = viewModel()
        assertEquals(1, vm.uiState.value.locations.size)

        vm.addLocation()
        vm.addLocation()
        assertEquals(3, vm.uiState.value.locations.size)

        vm.removeLocation(2)
        assertEquals(2, vm.uiState.value.locations.size)

        // Sentinel: removing past the minimum is a no-op.
        vm.removeLocation(0)
        vm.removeLocation(0)
        assertEquals(1, vm.uiState.value.locations.size)
    }

    @Test
    fun `saveProgress with no persisted event creates a draft via the repository`() = runTest {
        val createdDetail = com.bounswe.group9.mobile.data.remote.EventDetailDto(
            id = "evt-1", host_id = "h1", host_username = null,
            title = "T", description = "D",
            start_datetime = "2026-06-01T10:00:00+00:00",
            end_datetime = "2026-06-01T12:00:00+00:00",
            visibility = "public", is_age_restricted = false,
            attendee_limit = null, attendee_count = 0, status = "draft",
            created_at = "2026-01-01T00:00:00Z", updated_at = "2026-01-01T00:00:00Z",
            is_bookmarked = null, attendance_status = null,
            going_count = 0, bookmark_count = 0, is_full = false,
            locations = emptyList(), categories = emptyList(),
            images = emptyList(), venue_metadata = null,
            equipment_requirements = emptyList(), segments = null
        )
        coEvery { repository.createEvent(any(), any()) } returns Result.success(createdDetail)

        val vm = viewModel()
        vm.init(token = "tok")
        advanceUntilIdle()
        vm.onTitleChange("Concert")
        vm.onDescriptionChange("Best night ever")
        vm.toggleCategory("c1")

        vm.saveProgress()
        advanceUntilIdle()

        assertEquals("evt-1", vm.uiState.value.persistedEventId)
        assertEquals("Draft saved.", vm.uiState.value.feedbackMessage)
    }

    @Test
    fun `addImageUri appends to selectedImageUris and removeImageUri removes it`() {
        val vm = viewModel()
        // android.net.Uri is an Android framework class — mocked by default in
        // unit tests. Use MockK proxies as opaque list values.
        val a = mockk<android.net.Uri>()
        val b = mockk<android.net.Uri>()

        vm.addImageUri(a)
        vm.addImageUri(b)
        assertEquals(listOf(a, b), vm.uiState.value.selectedImageUris)

        vm.removeImageUri(a)
        assertEquals(listOf(b), vm.uiState.value.selectedImageUris)
    }

    @Test
    fun `stepCompleted reflects required-field state`() {
        val vm = viewModel()
        // All steps incomplete on a fresh form.
        assertTrue((0..2).none { vm.uiState.value.stepCompleted(it) })

        vm.onTitleChange("X"); vm.onDescriptionChange("X"); vm.toggleCategory("c1")
        assertTrue(vm.uiState.value.stepCompleted(0))
    }
}
