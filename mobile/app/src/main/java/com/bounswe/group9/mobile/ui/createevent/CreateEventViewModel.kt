package com.bounswe.group9.mobile.ui.createevent

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bounswe.group9.mobile.data.remote.CategoryDto
import com.bounswe.group9.mobile.data.remote.EventCreateRequest
import com.bounswe.group9.mobile.data.remote.EventDetailDto
import com.bounswe.group9.mobile.data.remote.EventUpdateRequest
import com.bounswe.group9.mobile.data.remote.EventImageDto
import com.bounswe.group9.mobile.data.remote.LocationRequest
import com.bounswe.group9.mobile.data.remote.NominatimClient
import com.bounswe.group9.mobile.data.remote.VenueMetadataRequest
import com.bounswe.group9.mobile.data.repository.EventRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

val EVENT_EDITOR_STEPS = listOf(
    "Event basics",
    "Schedule",
    "Location",
    "Media",
    "Venue & accessibility",
    "Settings",
    "Review & publish"
)

enum class FeedbackTone { Success, Error, Info }

data class CreateEventUiState(
    val currentStep: Int = 0,
    // Step 0
    val title: String = "",
    val description: String = "",
    val selectedCategoryIds: Set<String> = emptySet(),
    val availableCategories: List<CategoryDto> = emptyList(),
    val categoriesLoading: Boolean = false,
    // Step 1
    val startDate: String = "",
    val startTime: String = "",
    val endDate: String = "",
    val endTime: String = "",
    val scheduleConfirmed: Boolean = false,
    // Step 2
    val locationName: String = "",
    val locationLat: String = "",
    val locationLng: String = "",
    val locationAddress: String = "",
    val locationAddressLoading: Boolean = false,
    val locationSuggestions: List<com.bounswe.group9.mobile.data.remote.NominatimResult> = emptyList(),
    val locationSuggestionsLoading: Boolean = false,
    val showLocationSuggestions: Boolean = false,
    // Step 3
    val selectedImageUris: List<Uri> = emptyList(),
    val uploadedImages: List<EventImageDto> = emptyList(),
    val isUploadingImages: Boolean = false,
    val imageUploadError: String? = null,
    // Step 4
    val healthRequirements: String = "",
    val wheelchairAccess: Boolean = false,
    val accessibleRestroom: Boolean = false,
    val elevatorAvailable: Boolean = false,
    val seatingAvailable: Boolean = false,
    val captionsSupport: Boolean = false,
    val quietFriendly: Boolean = false,
    // Step 5
    val visibility: String = "public",
    val isAgeRestricted: Boolean = false,
    val attendeeLimitEnabled: Boolean = false,
    val attendeeLimit: String = "",
    val settingsConfirmed: Boolean = false,
    // Operation
    val isSaving: Boolean = false,
    val isPublishing: Boolean = false,
    val submitError: String? = null,
    val feedbackMessage: String? = null,
    val feedbackTone: FeedbackTone = FeedbackTone.Info,
    val persistedEventId: String? = null,
    val successEventId: String? = null,
    val isEditMode: Boolean = false,
    val editEventId: String? = null,
    // Whether event has already started (edit mode) — restricts schedule/location edits
    val eventAlreadyStarted: Boolean = false,
    // Steps that are incomplete (used in Review step UI)
    val missingSteps: List<Int> = emptyList(),
    // Field errors
    val titleError: String? = null,
    val descriptionError: String? = null,
    val categoryError: String? = null,
    val startError: String? = null,
    val endError: String? = null,
    val locationError: String? = null
) {
    fun stepCompleted(step: Int): Boolean = when (step) {
        0 -> title.isNotBlank() && description.isNotBlank() && selectedCategoryIds.isNotEmpty()
        1 -> scheduleConfirmed && startDate.isNotBlank() && startTime.isNotBlank() && endDate.isNotBlank() && endTime.isNotBlank()
        2 -> locationName.isNotBlank() && locationLat.toDoubleOrNull() != null && locationLng.toDoubleOrNull() != null
        3 -> true  // Media is optional — backend allows publishing without images
        4 -> true
        5 -> settingsConfirmed
        6 -> (0..5).all { stepCompleted(it) }
        else -> false
    }

    fun canSelectStep(step: Int): Boolean {
        if (isEditMode) return true
        return step <= currentStep || (0 until step).all { stepCompleted(it) }
    }
}

class CreateEventViewModel(
    private val repository: EventRepository = EventRepository()
) : ViewModel() {

    private val _uiState = MutableStateFlow(CreateEventUiState())
    val uiState: StateFlow<CreateEventUiState> = _uiState.asStateFlow()
    private var currentToken: String? = null
    private var locationSearchJob: kotlinx.coroutines.Job? = null

    fun init(token: String?, editEvent: EventDetailDto? = null) {
        currentToken = token
        // Guard: unauthenticated users cannot access create/edit
        if (token == null) {
            update { copy(submitError = "You must be signed in to create or edit events.") }
            return
        }
        loadCategories()
        if (editEvent != null) prefillForEdit(editEvent)
        else update { copy(feedbackMessage = "You can save progress anytime while building the event.", feedbackTone = FeedbackTone.Info) }
    }

    private fun prefillForEdit(event: EventDetailDto) {
        val isoParser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.getDefault())
        val dateFmt = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
        val timeFmt = SimpleDateFormat("HH:mm", Locale.getDefault())
        fun parse(iso: String): Date? = try { isoParser.parse(iso) } catch (_: Exception) { null }
        val startD = parse(event.start_datetime)
        val endD = parse(event.end_datetime)
        val loc = event.locations.firstOrNull { it.is_primary } ?: event.locations.firstOrNull()
        // Check if event has already started — restricts schedule & location edits
        val alreadyStarted = startD != null && startD <= Date()
        update {
            copy(
                isEditMode = true, editEventId = event.id, persistedEventId = event.id,
                title = event.title, description = event.description,
                startDate = startD?.let { dateFmt.format(it) } ?: "",
                startTime = startD?.let { timeFmt.format(it) } ?: "",
                endDate = endD?.let { dateFmt.format(it) } ?: "",
                endTime = endD?.let { timeFmt.format(it) } ?: "",
                locationName = loc?.name ?: "", locationLat = loc?.latitude?.toString() ?: "", locationLng = loc?.longitude?.toString() ?: "", locationAddress = loc?.location_address ?: "",
                visibility = event.visibility, isAgeRestricted = event.is_age_restricted,
                attendeeLimitEnabled = event.attendee_limit != null, attendeeLimit = event.attendee_limit?.toString() ?: "",
                selectedCategoryIds = event.categories.map { it.id }.toSet(),
                uploadedImages = event.images,
                scheduleConfirmed = true, settingsConfirmed = true,
                eventAlreadyStarted = alreadyStarted,
                feedbackMessage = if (alreadyStarted)
                    "This event has already started — schedule and location cannot be changed."
                else null,
                feedbackTone = FeedbackTone.Info
            )
        }
    }

    private fun loadCategories() {
        update { copy(categoriesLoading = true) }
        viewModelScope.launch {
            repository.getCategories().fold(
                onSuccess = { cats -> update { copy(availableCategories = cats, categoriesLoading = false) } },
                onFailure = { update { copy(categoriesLoading = false) } }
            )
        }
    }

    fun goToStep(step: Int) {
        if (!_uiState.value.canSelectStep(step)) return
        update { copy(currentStep = step, feedbackMessage = null, submitError = null) }
    }

    fun nextStep() {
        if (!validateCurrentStep()) return
        val s = _uiState.value
        if (s.currentStep == 1) update { copy(scheduleConfirmed = true) }
        if (s.currentStep == 5) update { copy(settingsConfirmed = true) }
        if (s.currentStep == 2 && s.persistedEventId == null) { createDraftThenAdvance(); return }
        update { copy(currentStep = (currentStep + 1).coerceAtMost(EVENT_EDITOR_STEPS.size - 1)) }
    }

    fun prevStep() = update { copy(currentStep = (currentStep - 1).coerceAtLeast(0), feedbackMessage = null, submitError = null) }

    fun onTitleChange(v: String) = update { copy(title = v, titleError = null) }
    fun onDescriptionChange(v: String) = update { copy(description = v, descriptionError = null) }
    fun toggleCategory(id: String) { val c = _uiState.value.selectedCategoryIds; update { copy(selectedCategoryIds = if (id in c) c - id else c + id, categoryError = null) } }
    fun onStartDateChange(v: String) = update { copy(startDate = v, startError = null) }
    fun onStartTimeChange(v: String) = update { copy(startTime = v, startError = null) }
    fun onEndDateChange(v: String) = update { copy(endDate = v, endError = null) }
    fun onEndTimeChange(v: String) = update { copy(endTime = v, endError = null) }
    fun onLocationNameChange(v: String) {
        update { copy(locationName = v, locationError = null, showLocationSuggestions = v.isNotBlank()) }
        locationSearchJob?.cancel()
        if (v.isNotBlank()) {
            locationSearchJob = viewModelScope.launch {
                kotlinx.coroutines.delay(400)
                update { copy(locationSuggestionsLoading = true) }
                val results = NominatimClient.suggest(v)
                update { copy(locationSuggestions = results, locationSuggestionsLoading = false) }
            }
        } else {
            update { copy(locationSuggestions = emptyList(), locationSuggestionsLoading = false) }
        }
    }

    fun onLocationSuggestionPicked(result: com.bounswe.group9.mobile.data.remote.NominatimResult) {
        locationSearchJob?.cancel()
        update {
            copy(
                locationName = result.shortName.ifBlank { result.displayName.split(",").first().trim() },
                locationLat = result.lat.toString(),
                locationLng = result.lng.toString(),
                locationSuggestions = emptyList(),
                showLocationSuggestions = false,
                locationError = null,
                locationAddressLoading = true
            )
        }
        viewModelScope.launch {
            val address = NominatimClient.reverseGeocode(result.lat, result.lng)
            update { copy(locationAddress = address ?: "", locationAddressLoading = false) }
        }
    }

    fun dismissLocationSuggestions() {
        update { copy(showLocationSuggestions = false, locationSuggestions = emptyList()) }
    }

    fun onLocationLatChange(v: String) = update { copy(locationLat = v, locationError = null) }
    fun onLocationLngChange(v: String) = update { copy(locationLng = v, locationError = null) }
    /** Called when the user taps the map in Step 2 — sets coordinates and kicks off reverse geocoding. */
    fun onLocationPicked(lat: Double, lng: Double) {
        update { copy(locationLat = lat.toString(), locationLng = lng.toString(), locationError = null, locationAddressLoading = true) }
        viewModelScope.launch {
            val address = NominatimClient.reverseGeocode(lat, lng)
            update { copy(locationAddress = address ?: "", locationAddressLoading = false) }
        }
    }
    fun onHealthRequirementsChange(v: String) = update { copy(healthRequirements = v) }
    fun onWheelchairAccessChange(v: Boolean) = update { copy(wheelchairAccess = v) }
    fun onAccessibleRestroomChange(v: Boolean) = update { copy(accessibleRestroom = v) }
    fun onElevatorAvailableChange(v: Boolean) = update { copy(elevatorAvailable = v) }
    fun onSeatingAvailableChange(v: Boolean) = update { copy(seatingAvailable = v) }
    fun onCaptionsSupportChange(v: Boolean) = update { copy(captionsSupport = v) }
    fun onQuietFriendlyChange(v: Boolean) = update { copy(quietFriendly = v) }
    fun onVisibilityChange(v: String) = update { copy(visibility = v) }
    fun onAgeRestrictedChange(v: Boolean) = update { copy(isAgeRestricted = v) }
    fun onAttendeeLimitEnabledChange(v: Boolean) = update { copy(attendeeLimitEnabled = v, attendeeLimit = if (!v) "" else attendeeLimit) }
    fun onAttendeeLimitChange(v: String) = update { copy(attendeeLimit = v.filter { it.isDigit() }) }
    fun addImageUri(uri: Uri) = update { copy(selectedImageUris = selectedImageUris + uri) }
    fun removeImageUri(uri: Uri) = update { copy(selectedImageUris = selectedImageUris - uri) }
    fun clearFeedback() = update { copy(feedbackMessage = null, submitError = null) }

    private fun validateCurrentStep(): Boolean = when (_uiState.value.currentStep) {
        0 -> { val s = _uiState.value; var ok = true
            if (s.title.isBlank()) { update { copy(titleError = "Title is required") }; ok = false }
            if (s.description.isBlank()) { update { copy(descriptionError = "Description is required") }; ok = false }
            if (s.selectedCategoryIds.isEmpty()) { update { copy(categoryError = "Select at least one category") }; ok = false }
            ok }
        1 -> { val s = _uiState.value; var ok = true
            if (s.startDate.isBlank() || s.startTime.isBlank()) { update { copy(startError = "Start date and time required") }; ok = false }
            if (s.endDate.isBlank() || s.endTime.isBlank()) { update { copy(endError = "End date and time required") }; ok = false }
            if (ok && !s.eventAlreadyStarted) {
                val fmt = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault())
                val start = try { fmt.parse("${s.startDate} ${s.startTime}") } catch (_: Exception) { null }
                val end = try { fmt.parse("${s.endDate} ${s.endTime}") } catch (_: Exception) { null }
                if (start != null && end != null && !end.after(start)) {
                    update { copy(endError = "End time must be after start time") }; ok = false
                }
            }
            ok }
        2 -> { val s = _uiState.value; var ok = true
            if (s.locationName.isBlank()) { update { copy(locationError = "Location name required") }; ok = false }
            val lat = s.locationLat.toDoubleOrNull(); val lng = s.locationLng.toDoubleOrNull()
            if (lat == null || lat < -90 || lat > 90 || lng == null || lng < -180 || lng > 180) { update { copy(locationError = "Valid latitude and longitude required") }; ok = false }
            ok }
        else -> true
    }

    private fun createDraftThenAdvance() {
        val token = currentToken ?: return
        val s = _uiState.value
        update { copy(isSaving = true) }
        viewModelScope.launch {
            repository.createEvent(token, buildCreateRequest(s, "draft")).fold(
                onSuccess = { event -> update { copy(persistedEventId = event.id, isSaving = false, currentStep = currentStep + 1, feedbackMessage = "Draft created. You can add media now.", feedbackTone = FeedbackTone.Success) } },
                onFailure = { e -> update { copy(isSaving = false, submitError = e.message ?: "Failed to create draft") } }
            )
        }
    }

    fun saveProgress() {
        val token = currentToken ?: return
        val s = _uiState.value
        update { copy(isSaving = true) }
        viewModelScope.launch {
            val result = if (s.persistedEventId != null) repository.updateEvent(token, s.persistedEventId, buildUpdateRequest(s))
            else repository.createEvent(token, buildCreateRequest(s, "draft"))
            result.fold(
                onSuccess = { event -> update { copy(persistedEventId = event.id, isSaving = false, feedbackMessage = if (isEditMode) "Changes saved." else "Draft saved.", feedbackTone = FeedbackTone.Success) } },
                onFailure = { e -> update { copy(isSaving = false, submitError = e.message ?: "Failed to save") } }
            )
        }
    }

    fun publish() {
        val token = currentToken ?: return
        val s = _uiState.value

        // Pre-publish validation: find incomplete required steps (0,1,2,5)
        val missing = listOf(0, 1, 2, 5).filter { !s.stepCompleted(it) }
        if (missing.isNotEmpty()) {
            update {
                copy(
                    currentStep = 6, // go to Review to show what's missing
                    missingSteps = missing,
                    feedbackMessage = "Complete all required steps before publishing.",
                    feedbackTone = FeedbackTone.Error
                )
            }
            return
        }

        update { copy(isPublishing = true, missingSteps = emptyList()) }
        viewModelScope.launch {
            val saveResult = if (s.persistedEventId != null) repository.updateEvent(token, s.persistedEventId, buildUpdateRequest(s))
            else repository.createEvent(token, buildCreateRequest(s, "draft"))
            saveResult.fold(
                onSuccess = { saved ->
                    repository.changeEventStatus(token, saved.id, "published").fold(
                        onSuccess = { pub -> update { copy(isPublishing = false, persistedEventId = pub.id, successEventId = pub.id, feedbackMessage = "Event published!", feedbackTone = FeedbackTone.Success) } },
                        onFailure = { e ->
                            val msg = e.message ?: "Failed to publish"
                            val goToMedia = msg.contains("image", ignoreCase = true)
                            update {
                                copy(
                                    isPublishing = false,
                                    submitError = msg,
                                    currentStep = if (goToMedia) 3 else currentStep
                                )
                            }
                        }
                    )
                },
                onFailure = { e -> update { copy(isPublishing = false, submitError = e.message ?: "Failed to save") } }
            )
        }
    }

    fun uploadImages(context: Context) {
        val token = currentToken ?: return
        val uris = _uiState.value.selectedImageUris
        if (uris.isEmpty()) return
        update { copy(isUploadingImages = true, imageUploadError = null) }
        viewModelScope.launch {
            // Auto-create draft first if it doesn't exist yet
            val eventId = _uiState.value.persistedEventId ?: run {
                val s = _uiState.value
                repository.createEvent(token, buildCreateRequest(s, "draft")).fold(
                    onSuccess = { event ->
                        update { copy(persistedEventId = event.id) }
                        event.id
                    },
                    onFailure = { e ->
                        update { copy(isUploadingImages = false, imageUploadError = "Could not create draft: ${e.message}") }
                        null
                    }
                )
            } ?: return@launch

            var hasError = false
            val uploaded = mutableListOf<EventImageDto>()
            for (uri in uris) {
                try {
                    val stream = context.contentResolver.openInputStream(uri) ?: continue
                    val bytes = stream.readBytes(); stream.close()
                    val mimeType = context.contentResolver.getType(uri) ?: "image/jpeg"
                    val part = MultipartBody.Part.createFormData("file", "image.jpg", bytes.toRequestBody(mimeType.toMediaTypeOrNull()))
                    repository.uploadEventImage(token, eventId, part).fold(
                        onSuccess = { img -> uploaded.add(img) },
                        onFailure = { hasError = true }
                    )
                } catch (_: Exception) { hasError = true }
            }
            update {
                copy(
                    isUploadingImages = false, selectedImageUris = emptyList(),
                    uploadedImages = uploadedImages + uploaded,
                    imageUploadError = if (hasError) "Some images failed to upload" else null,
                    feedbackMessage = if (!hasError && uploaded.isNotEmpty()) "${uploaded.size} image${if (uploaded.size == 1) "" else "s"} uploaded." else null,
                    feedbackTone = FeedbackTone.Success
                )
            }
        }
    }

    private fun buildIso(date: String, time: String, isEnd: Boolean = false): String {
        return try {
            val parser = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US)
            val parsed = parser.parse("$date $time")
            if (parsed == null) {
                // Return a valid future datetime fallback for drafts
                return if (isEnd) "2099-12-31T23:59:00+00:00" else "2099-12-31T00:00:00+00:00"
            }
            val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US)
            formatter.format(parsed)
        } catch (_: Exception) {
            if (isEnd) "2099-12-31T23:59:00+00:00" else "2099-12-31T00:00:00+00:00"
        }
    }

    private fun buildVenueMetadata(s: CreateEventUiState) = VenueMetadataRequest(
        health_requirements = s.healthRequirements.ifBlank { null },
        wheelchair_access = s.wheelchairAccess,
        accessible_restroom = s.accessibleRestroom,
        elevator_available = s.elevatorAvailable,
        seating_available = s.seatingAvailable,
        captions_support = s.captionsSupport,
        quiet_friendly = s.quietFriendly
    )

    private fun buildCreateRequest(s: CreateEventUiState, status: String): EventCreateRequest {
        val safeTitle = s.title.ifBlank { "Untitled Event" }
        val safeDesc = s.description.ifBlank { "No description provided yet." }
        val safeStart = buildIso(s.startDate, s.startTime)
        val safeEnd = buildIso(s.endDate, s.endTime, isEnd = true)
        val safeLocName = s.locationName.ifBlank { "TBD" }
        val safeLat = s.locationLat.toDoubleOrNull() ?: 0.0
        val safeLng = s.locationLng.toDoubleOrNull() ?: 0.0
        val safeCategoryIds = s.selectedCategoryIds.toList().ifEmpty {
            s.availableCategories.firstOrNull()?.id?.let { listOf(it) } ?: emptyList()
        }

        return EventCreateRequest(
            title = safeTitle, description = safeDesc,
            start_datetime = safeStart, end_datetime = safeEnd,
            visibility = s.visibility, is_age_restricted = s.isAgeRestricted,
            attendee_limit = if (s.attendeeLimitEnabled) s.attendeeLimit.toIntOrNull() else null,
            status = status, category_ids = safeCategoryIds,
            locations = listOf(LocationRequest(safeLocName, safeLat, safeLng, location_address = s.locationAddress.takeIf { it.isNotBlank() })),
            venue_metadata = buildVenueMetadata(s)
        )
    }

    private fun buildUpdateRequest(s: CreateEventUiState): EventUpdateRequest {
        val safeTitle = s.title.ifBlank { "Untitled Event" }
        val safeDesc = s.description.ifBlank { "No description provided yet." }
        val safeStart = buildIso(s.startDate, s.startTime)
        val safeEnd = buildIso(s.endDate, s.endTime, isEnd = true)
        val safeLocName = s.locationName.ifBlank { "TBD" }
        val safeLat = s.locationLat.toDoubleOrNull() ?: 0.0
        val safeLng = s.locationLng.toDoubleOrNull() ?: 0.0
        val safeCategoryIds = s.selectedCategoryIds.toList().ifEmpty {
            s.availableCategories.firstOrNull()?.id?.let { listOf(it) } ?: emptyList()
        }

        return EventUpdateRequest(
            title = safeTitle, description = safeDesc,
            start_datetime = safeStart, end_datetime = safeEnd,
            visibility = s.visibility, is_age_restricted = s.isAgeRestricted,
            attendee_limit = if (s.attendeeLimitEnabled) s.attendeeLimit.toIntOrNull() else null,
            clear_attendee_limit = !s.attendeeLimitEnabled, category_ids = safeCategoryIds,
            locations = listOf(LocationRequest(safeLocName, safeLat, safeLng, location_address = s.locationAddress.takeIf { it.isNotBlank() })),
            venue_metadata = buildVenueMetadata(s)
        )
    }

    private fun update(block: CreateEventUiState.() -> CreateEventUiState) { _uiState.value = _uiState.value.block() }
}