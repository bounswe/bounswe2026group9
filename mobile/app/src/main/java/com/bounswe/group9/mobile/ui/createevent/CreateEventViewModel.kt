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
import com.bounswe.group9.mobile.data.remote.SegmentRequest
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

data class LocationEntry(
    val name: String = "",
    val lat: String = "",
    val lng: String = "",
    val segmentStartDate: String = "",
    val segmentStartTime: String = "",
    val segmentEndDate: String = "",
    val segmentEndTime: String = "",
    val segmentDescription: String = "",
    val showSegmentFields: Boolean = false
)

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
    // Step 2 — multi-location; first entry is always primary
    val locations: List<LocationEntry> = listOf(LocationEntry()),
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
        2 -> {
            val primary = locations.firstOrNull()
            primary != null && primary.name.isNotBlank() &&
                primary.lat.toDoubleOrNull() != null && primary.lng.toDoubleOrNull() != null
        }
        3 -> true
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

    fun init(token: String?, editEvent: EventDetailDto? = null) {
        currentToken = token
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
        val alreadyStarted = startD != null && startD <= Date()

        val segmentsByLocId = event.segments?.groupBy { it.location_id } ?: emptyMap()
        val locEntries = event.locations.sortedBy { it.order_index }.map { loc ->
            val seg = segmentsByLocId[loc.id]?.firstOrNull()
            LocationEntry(
                name = loc.name,
                lat = loc.latitude.toString(),
                lng = loc.longitude.toString(),
                segmentStartDate = seg?.let { parseIsoDate(it.start_datetime, isoParser, dateFmt) } ?: "",
                segmentStartTime = seg?.let { parseIsoTime(it.start_datetime, isoParser, timeFmt) } ?: "",
                segmentEndDate = seg?.let { parseIsoDate(it.end_datetime, isoParser, dateFmt) } ?: "",
                segmentEndTime = seg?.let { parseIsoTime(it.end_datetime, isoParser, timeFmt) } ?: "",
                segmentDescription = seg?.description ?: "",
                showSegmentFields = seg != null
            )
        }.ifEmpty { listOf(LocationEntry()) }

        update {
            copy(
                isEditMode = true, editEventId = event.id, persistedEventId = event.id,
                title = event.title, description = event.description,
                startDate = startD?.let { dateFmt.format(it) } ?: "",
                startTime = startD?.let { timeFmt.format(it) } ?: "",
                endDate = endD?.let { dateFmt.format(it) } ?: "",
                endTime = endD?.let { timeFmt.format(it) } ?: "",
                locations = locEntries,
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

    private fun parseIsoDate(iso: String, parser: SimpleDateFormat, fmt: SimpleDateFormat): String =
        try { fmt.format(parser.parse(iso)!!) } catch (_: Exception) { "" }

    private fun parseIsoTime(iso: String, parser: SimpleDateFormat, fmt: SimpleDateFormat): String =
        try { fmt.format(parser.parse(iso)!!) } catch (_: Exception) { "" }

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
    fun toggleCategory(id: String) {
        val c = _uiState.value.selectedCategoryIds
        update { copy(selectedCategoryIds = if (id in c) c - id else c + id, categoryError = null) }
    }
    fun onStartDateChange(v: String) = update { copy(startDate = v, startError = null) }
    fun onStartTimeChange(v: String) = update { copy(startTime = v, startError = null) }
    fun onEndDateChange(v: String) = update { copy(endDate = v, endError = null) }
    fun onEndTimeChange(v: String) = update { copy(endTime = v, endError = null) }

    // ── Multi-location management ────────────────────────────────────────────────

    fun onLocationNameChange(index: Int, name: String) = update {
        copy(locations = locations.mapIndexed { i, l -> if (i == index) l.copy(name = name) else l }, locationError = null)
    }

    fun onLocationPicked(index: Int, lat: Double, lng: Double) = update {
        copy(locations = locations.mapIndexed { i, l ->
            if (i == index) l.copy(lat = lat.toString(), lng = lng.toString()) else l
        }, locationError = null)
    }

    fun addLocation() = update { copy(locations = locations + LocationEntry()) }

    fun removeLocation(index: Int) = update {
        if (locations.size <= 1) return@update this
        copy(locations = locations.filterIndexed { i, _ -> i != index })
    }

    /**
     * Reorder a stop within the locations list. Index numbers shown in the UI
     * are derived from the list position, so a reorder here automatically
     * re-numbers the stops (issue #160 AC #1).
     */
    fun moveLocation(fromIndex: Int, toIndex: Int) = update {
        if (fromIndex == toIndex) return@update this
        if (fromIndex !in locations.indices || toIndex !in locations.indices) return@update this
        val mutable = locations.toMutableList()
        val moved = mutable.removeAt(fromIndex)
        mutable.add(toIndex, moved)
        copy(locations = mutable.toList(), locationError = null)
    }

    fun toggleSegmentFields(index: Int) = update {
        copy(locations = locations.mapIndexed { i, l ->
            if (i == index) l.copy(showSegmentFields = !l.showSegmentFields) else l
        })
    }

    fun onSegmentStartDateChange(index: Int, date: String) = update {
        copy(locations = locations.mapIndexed { i, l -> if (i == index) l.copy(segmentStartDate = date) else l })
    }

    fun onSegmentStartTimeChange(index: Int, time: String) = update {
        copy(locations = locations.mapIndexed { i, l -> if (i == index) l.copy(segmentStartTime = time) else l })
    }

    fun onSegmentEndDateChange(index: Int, date: String) = update {
        copy(locations = locations.mapIndexed { i, l -> if (i == index) l.copy(segmentEndDate = date) else l })
    }

    fun onSegmentEndTimeChange(index: Int, time: String) = update {
        copy(locations = locations.mapIndexed { i, l -> if (i == index) l.copy(segmentEndTime = time) else l })
    }

    fun onSegmentDescriptionChange(index: Int, desc: String) = update {
        copy(locations = locations.mapIndexed { i, l -> if (i == index) l.copy(segmentDescription = desc) else l })
    }

    // ── Venue & Accessibility ────────────────────────────────────────────────────

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
        0 -> {
            val s = _uiState.value; var ok = true
            if (s.title.isBlank()) { update { copy(titleError = "Title is required") }; ok = false }
            if (s.description.isBlank()) { update { copy(descriptionError = "Description is required") }; ok = false }
            if (s.selectedCategoryIds.isEmpty()) { update { copy(categoryError = "Select at least one category") }; ok = false }
            ok
        }
        1 -> {
            val s = _uiState.value; var ok = true
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
            ok
        }
        2 -> {
            val s = _uiState.value; var ok = true
            val primary = s.locations.firstOrNull()
            if (primary == null || primary.name.isBlank()) { update { copy(locationError = "Location name required") }; ok = false }
            if (ok) {
                val lat = primary!!.lat.toDoubleOrNull(); val lng = primary.lng.toDoubleOrNull()
                if (lat == null || lat < -90 || lat > 90 || lng == null || lng < -180 || lng > 180) {
                    update { copy(locationError = "Valid latitude and longitude required for the primary location") }; ok = false
                }
            }
            if (ok) {
                val fmt = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault())
                val eventStart = try { fmt.parse("${s.startDate} ${s.startTime}") } catch (_: Exception) { null }
                val eventEnd   = try { fmt.parse("${s.endDate} ${s.endTime}") } catch (_: Exception) { null }

                // Collect stops that have complete segment timing
                val timedSegs = s.locations.mapIndexedNotNull { i, loc ->
                    if (loc.segmentStartDate.isNotBlank() && loc.segmentStartTime.isNotBlank() &&
                        loc.segmentEndDate.isNotBlank() && loc.segmentEndTime.isNotBlank()) {
                        val segStart = try { fmt.parse("${loc.segmentStartDate} ${loc.segmentStartTime}") } catch (_: Exception) { null }
                        val segEnd   = try { fmt.parse("${loc.segmentEndDate} ${loc.segmentEndTime}") } catch (_: Exception) { null }
                        if (segStart != null && segEnd != null) Triple(i + 1, segStart, segEnd) else null
                    } else null
                }

                for ((stopNum, segStart, segEnd) in timedSegs) {
                    if (!segEnd.after(segStart)) {
                        update { copy(locationError = "Stop $stopNum: end time must be after start time") }; ok = false; break
                    }
                    if (eventStart != null && segStart.before(eventStart)) {
                        update { copy(locationError = "Stop $stopNum timing must not be before the event start") }; ok = false; break
                    }
                    if (eventEnd != null && segEnd.after(eventEnd)) {
                        update { copy(locationError = "Stop $stopNum timing must not exceed the event end") }; ok = false; break
                    }
                }

                // Consecutive timed stops must not overlap (stop N+1 must start at or after stop N ends)
                if (ok) {
                    for (i in 0 until timedSegs.size - 1) {
                        val (prevNum, _, prevEnd) = timedSegs[i]
                        val (nextNum, nextStart, _) = timedSegs[i + 1]
                        if (nextStart.before(prevEnd)) {
                            update { copy(locationError = "Stop $nextNum must start after Stop $prevNum ends") }; ok = false; break
                        }
                    }
                }
            }
            ok
        }
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

        val missing = listOf(0, 1, 2, 5).filter { !s.stepCompleted(it) }
        if (missing.isNotEmpty()) {
            update {
                copy(
                    currentStep = 6,
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

    private fun buildLocationRequests(s: CreateEventUiState): List<LocationRequest> =
        s.locations.ifEmpty { listOf(LocationEntry()) }.mapIndexed { i, loc ->
            LocationRequest(
                name = loc.name.ifBlank { "Stop ${i + 1}" },
                latitude = loc.lat.toDoubleOrNull() ?: 0.0,
                longitude = loc.lng.toDoubleOrNull() ?: 0.0,
                is_primary = (i == 0),
                order_index = i
            )
        }

    private fun buildSegmentRequests(s: CreateEventUiState): List<SegmentRequest>? {
        val segs = s.locations.mapIndexedNotNull { i, loc ->
            if (loc.segmentStartDate.isNotBlank() && loc.segmentStartTime.isNotBlank() &&
                loc.segmentEndDate.isNotBlank() && loc.segmentEndTime.isNotBlank()) {
                SegmentRequest(
                    location_index = i,
                    order_index = i,
                    start_datetime = buildIso(loc.segmentStartDate, loc.segmentStartTime),
                    end_datetime = buildIso(loc.segmentEndDate, loc.segmentEndTime, isEnd = true),
                    description = loc.segmentDescription.ifBlank { null }
                )
            } else null
        }
        return if (segs.isNotEmpty()) segs else null
    }

    private fun buildCreateRequest(s: CreateEventUiState, status: String): EventCreateRequest {
        val safeTitle = s.title.ifBlank { "Untitled Event" }
        val safeDesc = s.description.ifBlank { "No description provided yet." }
        val safeStart = buildIso(s.startDate, s.startTime)
        val safeEnd = buildIso(s.endDate, s.endTime, isEnd = true)
        val safeCategoryIds = s.selectedCategoryIds.toList().ifEmpty {
            s.availableCategories.firstOrNull()?.id?.let { listOf(it) } ?: emptyList()
        }
        return EventCreateRequest(
            title = safeTitle, description = safeDesc,
            start_datetime = safeStart, end_datetime = safeEnd,
            visibility = s.visibility, is_age_restricted = s.isAgeRestricted,
            attendee_limit = if (s.attendeeLimitEnabled) s.attendeeLimit.toIntOrNull() else null,
            status = status, category_ids = safeCategoryIds,
            locations = buildLocationRequests(s),
            segments = buildSegmentRequests(s),
            venue_metadata = buildVenueMetadata(s)
        )
    }

    private fun buildUpdateRequest(s: CreateEventUiState): EventUpdateRequest {
        val safeTitle = s.title.ifBlank { "Untitled Event" }
        val safeDesc = s.description.ifBlank { "No description provided yet." }
        val safeStart = buildIso(s.startDate, s.startTime)
        val safeEnd = buildIso(s.endDate, s.endTime, isEnd = true)
        val safeCategoryIds = s.selectedCategoryIds.toList().ifEmpty {
            s.availableCategories.firstOrNull()?.id?.let { listOf(it) } ?: emptyList()
        }
        return EventUpdateRequest(
            title = safeTitle, description = safeDesc,
            start_datetime = safeStart, end_datetime = safeEnd,
            visibility = s.visibility, is_age_restricted = s.isAgeRestricted,
            attendee_limit = if (s.attendeeLimitEnabled) s.attendeeLimit.toIntOrNull() else null,
            clear_attendee_limit = !s.attendeeLimitEnabled, category_ids = safeCategoryIds,
            locations = buildLocationRequests(s),
            segments = buildSegmentRequests(s),
            venue_metadata = buildVenueMetadata(s)
        )
    }

    private fun update(block: CreateEventUiState.() -> CreateEventUiState) { _uiState.value = _uiState.value.block() }
}
