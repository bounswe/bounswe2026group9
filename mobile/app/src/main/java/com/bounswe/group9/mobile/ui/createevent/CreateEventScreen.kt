package com.bounswe.group9.mobile.ui.createevent

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.ScrollState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.AddPhotoAlternate
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import java.util.Date
import java.util.Locale
import com.bounswe.group9.mobile.data.remote.EventDetailDto
import com.bounswe.group9.mobile.ui.theme.BrandDark
import com.bounswe.group9.mobile.ui.theme.BrandMid
import com.bounswe.group9.mobile.ui.theme.BrandSurfaceLight

// ── Brand colours ─────────────────────────────────────────────────────────────

private val StepActive   = BrandDark
private val StepDone     = BrandMid
private val StepInactive = Color(0xFFBDB5B0)
private val FeedbackSuccessBg = Color(0xFFECFDF5)
private val FeedbackSuccessFg = Color(0xFF065F46)
private val FeedbackErrorBg   = Color(0xFFFEF2F2)
private val FeedbackErrorFg   = Color(0xFF991B1B)
private val FeedbackInfoBg    = Color(0xFFF5F3F0)
private val FeedbackInfoFg    = Color(0xFF493628)

// ── Screen entry ──────────────────────────────────────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CreateEventScreen(
    token: String?,
    editEvent: EventDetailDto? = null,
    onBack: () -> Unit,
    onEventSaved: (eventId: String) -> Unit,
    viewModel: CreateEventViewModel = remember { CreateEventViewModel() }
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val snackbar = remember { SnackbarHostState() }
    var showStepDrawer by remember { mutableStateOf(false) }

    LaunchedEffect(token, editEvent) { viewModel.init(token, editEvent) }
    LaunchedEffect(uiState.successEventId) { uiState.successEventId?.let { onEventSaved(it) } }
    LaunchedEffect(uiState.submitError) {
        uiState.submitError?.let { snackbar.showSnackbar(it); viewModel.clearFeedback() }
    }

    // Guard: unauthenticated
    if (token == null) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp),
                modifier = Modifier.padding(32.dp)
            ) {
                Icon(Icons.Default.Lock, null, modifier = Modifier.size(48.dp), tint = BrandMid)
                Text("Sign in required", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = BrandDark)
                Text("You must be signed in to create or edit events.", style = MaterialTheme.typography.bodyMedium, color = Color(0xFF78716C))
                Button(onClick = onBack, colors = ButtonDefaults.buttonColors(containerColor = BrandDark)) {
                    Text("Go back")
                }
            }
        }
        return
    }

    val imagePickerLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.GetMultipleContents()
    ) { uris: List<Uri> -> uris.forEach { viewModel.addImageUri(it) } }

    if (showStepDrawer) {
        StepDrawer(
            steps = EVENT_EDITOR_STEPS,
            currentStep = uiState.currentStep,
            uiState = uiState,
            onStepSelect = { viewModel.goToStep(it); showStepDrawer = false },
            onDismiss = { showStepDrawer = false }
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            if (uiState.isEditMode) "Edit Event" else "Create Event",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold
                        )
                        Text(
                            "Step ${uiState.currentStep + 1} of ${EVENT_EDITOR_STEPS.size}",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { showStepDrawer = true }) {
                        Icon(Icons.Default.Menu, "Steps")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = BrandDark,
                    titleContentColor = Color.White,
                    navigationIconContentColor = Color.White,
                    actionIconContentColor = Color.White
                )
            )
        },
        bottomBar = {
            BottomNavBar(
                uiState = uiState,
                onBack = { viewModel.prevStep() },
                onNext = { viewModel.nextStep() },
                onSave = { viewModel.saveProgress() },
                onPublish = { viewModel.publish() }
            )
        },
        containerColor = Color(0xFFF5F3F0)
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            // Step progress bar
            StepProgressBar(
                currentStep = uiState.currentStep,
                totalSteps = EVENT_EDITOR_STEPS.size
            )

            val scrollState = rememberScrollState()

            Box(modifier = Modifier.weight(1f)) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(scrollState)
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Feedback banner
                    uiState.feedbackMessage?.let { msg ->
                        FeedbackBanner(message = msg, tone = uiState.feedbackTone)
                    }

                    // Step header
                    StepHeader(
                        stepIndex = uiState.currentStep,
                        title = EVENT_EDITOR_STEPS[uiState.currentStep],
                        description = STEP_DESCRIPTIONS[uiState.currentStep]
                    )

                    // Step content with slide animation
                    AnimatedContent(
                        targetState = uiState.currentStep,
                        transitionSpec = {
                            if (targetState > initialState)
                                (slideInHorizontally { it } + fadeIn()) togetherWith (slideOutHorizontally { -it } + fadeOut())
                            else
                                (slideInHorizontally { -it } + fadeIn()) togetherWith (slideOutHorizontally { it } + fadeOut())
                        },
                        label = "step"
                    ) { step ->
                        when (step) {
                            0 -> BasicsStep(uiState, viewModel)
                            1 -> ScheduleStep(uiState, viewModel)
                            2 -> LocationStep(uiState, viewModel)
                            3 -> MediaStep(uiState, viewModel, context, imagePickerLauncher)
                            4 -> VenueStep(uiState, viewModel)
                            5 -> SettingsStep(uiState, viewModel)
                            6 -> ReviewStep(uiState, viewModel)
                            else -> BasicsStep(uiState, viewModel)
                        }
                    }

                    Spacer(Modifier.height(8.dp))
                }

                // Scrollbar
                ScrollbarIndicator(
                    scrollState = scrollState,
                    modifier = Modifier.align(Alignment.CenterEnd).fillMaxHeight().width(4.dp)
                )
            }
        }
    }
}

// ── Step progress bar ─────────────────────────────────────────────────────────

@Composable
private fun StepProgressBar(currentStep: Int, totalSteps: Int) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(BrandDark)
            .padding(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        repeat(totalSteps) { index ->
            val fraction = when {
                index < currentStep -> 1f
                index == currentStep -> 1f
                else -> 0f
            }
            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(3.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(Color.White.copy(alpha = 0.25f))
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxHeight()
                        .fillMaxWidth(fraction)
                        .background(if (index <= currentStep) Color.White else Color.Transparent)
                )
            }
        }
    }
}

// ── Step header ───────────────────────────────────────────────────────────────

private val STEP_DESCRIPTIONS = listOf(
    "Name the event, describe the vibe, and tag the right categories.",
    "Choose a future timeslot and make sure the end time wraps after the start.",
    "Add the primary venue — name it and enter the coordinates.",
    "Upload the cover and supporting images for the event gallery.",
    "Optional venue details help attendees understand accessibility and logistics.",
    "Choose whether the event is visible to everyone or only to approved viewers.",
    "Review everything, make final adjustments, then publish."
)

@Composable
private fun StepHeader(stepIndex: Int, title: String, description: String) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(
            "Step ${stepIndex + 1} of ${EVENT_EDITOR_STEPS.size}",
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
            letterSpacing = 1.5.sp,
            color = BrandMid
        )
        Text(title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = BrandDark)
        Text(description, style = MaterialTheme.typography.bodyMedium, color = Color(0xFF78716C))
    }
}

// ── Step drawer (modal) ───────────────────────────────────────────────────────

@Composable
private fun StepDrawer(
    steps: List<String>,
    currentStep: Int,
    uiState: CreateEventUiState,
    onStepSelect: (Int) -> Unit,
    onDismiss: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.4f))
            .clickable(onClick = onDismiss)
    ) {
        Surface(
            modifier = Modifier
                .fillMaxHeight()
                .fillMaxWidth(0.82f)
                .align(Alignment.CenterStart)
                .clickable(onClick = {}), // prevent dismiss on surface tap
            color = MaterialTheme.colorScheme.surface,
            shadowElevation = 16.dp
        ) {
            Column {
                // Header
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(BrandDark)
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("Event steps", style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.SemiBold)
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, "Close", tint = Color.White)
                    }
                }

                Column(
                    modifier = Modifier
                        .verticalScroll(rememberScrollState())
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(0.dp)
                ) {
                    steps.forEachIndexed { index, step ->
                        val isActive = index == currentStep
                        val isComplete = uiState.stepCompleted(index)
                        val canSelect = uiState.canSelectStep(index)

                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(12.dp))
                                .then(if (canSelect) Modifier.clickable { onStepSelect(index) } else Modifier)
                                .padding(horizontal = 8.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.Top,
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                // Step circle
                                Box(
                                    modifier = Modifier
                                        .size(32.dp)
                                        .clip(CircleShape)
                                        .background(
                                            when {
                                                isActive -> StepActive
                                                isComplete -> StepDone
                                                else -> Color(0xFFE8E3DF)
                                            }
                                        ),
                                    contentAlignment = Alignment.Center
                                ) {
                                    if (isComplete && !isActive) {
                                        Icon(Icons.Default.Check, null, tint = Color.White, modifier = Modifier.size(16.dp))
                                    } else {
                                        Text(
                                            "${index + 1}",
                                            color = if (isActive || isComplete) Color.White else Color(0xFF9C9390),
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 13.sp
                                        )
                                    }
                                }
                                // Connector line
                                if (index < steps.size - 1) {
                                    Box(
                                        modifier = Modifier
                                            .width(2.dp)
                                            .height(24.dp)
                                            .background(if (isComplete) StepDone else Color(0xFFE0DAD6))
                                    )
                                }
                            }

                            Text(
                                step,
                                modifier = Modifier.padding(top = 6.dp),
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = if (isActive) FontWeight.SemiBold else FontWeight.Normal,
                                color = when {
                                    isActive -> BrandDark
                                    isComplete -> MaterialTheme.colorScheme.onSurface
                                    canSelect -> MaterialTheme.colorScheme.onSurfaceVariant
                                    else -> Color(0xFFBDB5B0)
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}

// ── Bottom nav bar ────────────────────────────────────────────────────────────

@Composable
private fun BottomNavBar(
    uiState: CreateEventUiState,
    onBack: () -> Unit,
    onNext: () -> Unit,
    onSave: () -> Unit,
    onPublish: () -> Unit
) {
    val isLastStep = uiState.currentStep == EVENT_EDITOR_STEPS.size - 1

    Surface(tonalElevation = 8.dp, shadowElevation = 8.dp) {
        Column(modifier = Modifier.fillMaxWidth()) {
            // Save draft row
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.End
            ) {
                OutlinedButton(
                    onClick = onSave,
                    enabled = !uiState.isSaving && !uiState.isPublishing,
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = BrandDark),
                    border = BorderStroke(1.dp, BrandMid.copy(alpha = 0.5f)),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 6.dp),
                    modifier = Modifier.height(36.dp)
                ) {
                    if (uiState.isSaving) {
                        CircularProgressIndicator(modifier = Modifier.size(14.dp), strokeWidth = 2.dp, color = BrandDark)
                        Spacer(Modifier.width(6.dp))
                        Text("Saving...", fontSize = 13.sp)
                    } else {
                        Text(if (uiState.isEditMode) "Save changes" else "Save draft", fontSize = 13.sp)
                    }
                }
            }

            HorizontalDivider(color = Color(0xFFE8E3DF))

            // Back / Next / Publish row
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (uiState.currentStep > 0) {
                    OutlinedButton(
                        onClick = onBack,
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = BrandDark),
                        border = BorderStroke(1.dp, BrandMid.copy(alpha = 0.4f))
                    ) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("Back")
                    }
                } else {
                    Spacer(Modifier.width(1.dp))
                }

                if (!isLastStep) {
                    Button(
                        onClick = onNext,
                        colors = ButtonDefaults.buttonColors(containerColor = BrandDark),
                        enabled = !uiState.isSaving
                    ) {
                        Text("Next")
                        Spacer(Modifier.width(4.dp))
                        Icon(Icons.AutoMirrored.Filled.ArrowForward, null, modifier = Modifier.size(16.dp))
                    }
                } else {
                    Button(
                        onClick = onPublish,
                        enabled = !uiState.isPublishing && !uiState.isSaving,
                        colors = ButtonDefaults.buttonColors(containerColor = BrandDark)
                    ) {
                        if (uiState.isPublishing) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp, color = Color.White)
                            Spacer(Modifier.width(6.dp))
                            Text("Publishing...")
                        } else {
                            Icon(Icons.Default.Star, null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("Publish event")
                        }
                    }
                }
            }
        }
    }
}

// ── Feedback banner ───────────────────────────────────────────────────────────

@Composable
private fun FeedbackBanner(message: String, tone: FeedbackTone) {
    val bg = when (tone) {
        FeedbackTone.Success -> FeedbackSuccessBg
        FeedbackTone.Error   -> FeedbackErrorBg
        FeedbackTone.Info    -> FeedbackInfoBg
    }
    val fg = when (tone) {
        FeedbackTone.Success -> FeedbackSuccessFg
        FeedbackTone.Error   -> FeedbackErrorFg
        FeedbackTone.Info    -> FeedbackInfoFg
    }
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = bg,
        border = BorderStroke(1.dp, fg.copy(alpha = 0.25f))
    ) {
        Text(message, modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp), style = MaterialTheme.typography.bodyMedium, color = fg)
    }
}

// ── Step 0: Basics ────────────────────────────────────────────────────────────

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun BasicsStep(uiState: CreateEventUiState, viewModel: CreateEventViewModel) {
    Column(verticalArrangement = Arrangement.spacedBy(20.dp)) {
        // Title
        StepCard {
            FieldLabel("Event title", helper = "Keep it short, clear, and easy to scan.")
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = uiState.title,
                onValueChange = viewModel::onTitleChange,
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("Give your event a memorable name") },
                isError = uiState.titleError != null,
                singleLine = true,
                supportingText = {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        uiState.titleError?.let { Text(it, color = MaterialTheme.colorScheme.error) } ?: Spacer(Modifier.width(1.dp))
                        Text("${uiState.title.length}/200", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            )
        }

        // Description
        StepCard {
            FieldLabel("Description", helper = "A few concrete details go a long way for attendance.")
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = uiState.description,
                onValueChange = viewModel::onDescriptionChange,
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("Tell people what the event is, who it's for, and what to expect.") },
                isError = uiState.descriptionError != null,
                minLines = 5,
                maxLines = 9,
                supportingText = {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        uiState.descriptionError?.let { Text(it, color = MaterialTheme.colorScheme.error) } ?: Spacer(Modifier.width(1.dp))
                        Text("${uiState.description.length}/2000", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            )
        }

        // Categories
        StepCard {
            FieldLabel("Categories", helper = "Choose the categories that best describe the event.")
            Spacer(Modifier.height(10.dp))
            if (uiState.categoriesLoading) {
                CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp, color = BrandMid)
            } else {
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    uiState.availableCategories.forEach { cat ->
                        val selected = cat.id in uiState.selectedCategoryIds
                        Surface(
                            shape = RoundedCornerShape(50),
                            color = if (selected) BrandDark else MaterialTheme.colorScheme.surface,
                            border = BorderStroke(1.dp, if (selected) BrandDark else Color(0xFF1C1917)),
                            modifier = Modifier.clickable { viewModel.toggleCategory(cat.id) }
                        ) {
                            Text(
                                cat.name,
                                modifier = Modifier.padding(horizontal = 14.dp, vertical = 7.dp),
                                color = if (selected) Color.White else MaterialTheme.colorScheme.onSurface,
                                fontSize = 13.sp,
                                fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal
                            )
                        }
                    }
                }
            }
            uiState.categoryError?.let { Spacer(Modifier.height(4.dp)); Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        }
    }
}

// ── Step 1: Schedule ──────────────────────────────────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ScheduleStep(uiState: CreateEventUiState, viewModel: CreateEventViewModel) {
    val readOnly = uiState.eventAlreadyStarted
    val dateFmt: java.text.SimpleDateFormat = remember { java.text.SimpleDateFormat("yyyy-MM-dd", Locale.US) }
    fun parseMs(d: String): Long? = try { dateFmt.parse(d)?.time } catch (_: Exception) { null }
    fun parseHour(t: String) = t.split(":").getOrNull(0)?.toIntOrNull() ?: 9
    fun parseMin(t: String) = t.split(":").getOrNull(1)?.toIntOrNull() ?: 0

    var showStartDate by remember { mutableStateOf(false) }
    var showStartTime by remember { mutableStateOf(false) }
    var showEndDate   by remember { mutableStateOf(false) }
    var showEndTime   by remember { mutableStateOf(false) }

    if (showStartDate) {
        val state = rememberDatePickerState(initialSelectedDateMillis = parseMs(uiState.startDate))
        DatePickerDialog(
            onDismissRequest = { showStartDate = false },
            confirmButton = {
                TextButton(onClick = {
                    state.selectedDateMillis?.let { viewModel.onStartDateChange(dateFmt.format(Date(it))) }
                    showStartDate = false
                }) { Text("OK") }
            },
            dismissButton = { TextButton(onClick = { showStartDate = false }) { Text("Cancel") } }
        ) { DatePicker(state = state) }
    }

    if (showStartTime) {
        val state = rememberTimePickerState(initialHour = parseHour(uiState.startTime), initialMinute = parseMin(uiState.startTime))
        AlertDialog(
            onDismissRequest = { showStartTime = false },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.onStartTimeChange(String.format("%02d:%02d", state.hour, state.minute))
                    showStartTime = false
                }) { Text("OK") }
            },
            dismissButton = { TextButton(onClick = { showStartTime = false }) { Text("Cancel") } },
            text = { TimePicker(state = state) }
        )
    }

    if (showEndDate) {
        val state = rememberDatePickerState(initialSelectedDateMillis = parseMs(uiState.endDate))
        DatePickerDialog(
            onDismissRequest = { showEndDate = false },
            confirmButton = {
                TextButton(onClick = {
                    state.selectedDateMillis?.let { viewModel.onEndDateChange(dateFmt.format(Date(it))) }
                    showEndDate = false
                }) { Text("OK") }
            },
            dismissButton = { TextButton(onClick = { showEndDate = false }) { Text("Cancel") } }
        ) { DatePicker(state = state) }
    }

    if (showEndTime) {
        val state = rememberTimePickerState(initialHour = parseHour(uiState.endTime), initialMinute = parseMin(uiState.endTime))
        AlertDialog(
            onDismissRequest = { showEndTime = false },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.onEndTimeChange(String.format("%02d:%02d", state.hour, state.minute))
                    showEndTime = false
                }) { Text("OK") }
            },
            dismissButton = { TextButton(onClick = { showEndTime = false }) { Text("Cancel") } },
            text = { TimePicker(state = state) }
        )
    }

    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        if (uiState.eventAlreadyStarted) {
            FeedbackBanner("This event has already started — schedule cannot be changed.", FeedbackTone.Error)
        } else if (!uiState.isEditMode && !uiState.scheduleConfirmed) {
            FeedbackBanner("Suggested times are prefilled for convenience. Review them and press Next to confirm.", FeedbackTone.Info)
        }

        StepCard {
            FieldLabel("Start")
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = uiState.startDate,
                    onValueChange = { if (!readOnly) viewModel.onStartDateChange(it) },
                    modifier = Modifier.weight(1f),
                    label = { Text("Date") },
                    placeholder = { Text("YYYY-MM-DD") },
                    singleLine = true,
                    isError = uiState.startError != null,
                    enabled = !readOnly,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    trailingIcon = {
                        if (!readOnly) IconButton(onClick = { showStartDate = true }) {
                            Icon(Icons.Default.DateRange, contentDescription = null, tint = BrandMid)
                        }
                    }
                )
                OutlinedTextField(
                    value = uiState.startTime,
                    onValueChange = { if (!readOnly) viewModel.onStartTimeChange(it) },
                    modifier = Modifier.weight(1f),
                    label = { Text("Time") },
                    placeholder = { Text("HH:MM") },
                    singleLine = true,
                    isError = uiState.startError != null,
                    enabled = !readOnly,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    trailingIcon = {
                        if (!readOnly) IconButton(onClick = { showStartTime = true }) {
                            Icon(Icons.Default.AccessTime, contentDescription = null, tint = BrandMid)
                        }
                    }
                )
            }
            uiState.startError?.let { Spacer(Modifier.height(4.dp)); Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        }

        StepCard {
            FieldLabel("End")
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = uiState.endDate,
                    onValueChange = { if (!readOnly) viewModel.onEndDateChange(it) },
                    modifier = Modifier.weight(1f),
                    label = { Text("Date") },
                    placeholder = { Text("YYYY-MM-DD") },
                    singleLine = true,
                    isError = uiState.endError != null,
                    enabled = !readOnly,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    trailingIcon = {
                        if (!readOnly) IconButton(onClick = { showEndDate = true }) {
                            Icon(Icons.Default.DateRange, contentDescription = null, tint = BrandMid)
                        }
                    }
                )
                OutlinedTextField(
                    value = uiState.endTime,
                    onValueChange = { if (!readOnly) viewModel.onEndTimeChange(it) },
                    modifier = Modifier.weight(1f),
                    label = { Text("Time") },
                    placeholder = { Text("HH:MM") },
                    singleLine = true,
                    isError = uiState.endError != null,
                    enabled = !readOnly,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    trailingIcon = {
                        if (!readOnly) IconButton(onClick = { showEndTime = true }) {
                            Icon(Icons.Default.AccessTime, contentDescription = null, tint = BrandMid)
                        }
                    }
                )
            }
            uiState.endError?.let { Spacer(Modifier.height(4.dp)); Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        }
    }
}

// ── Step 2: Location ──────────────────────────────────────────────────────────

@Composable
private fun LocationStep(uiState: CreateEventUiState, viewModel: CreateEventViewModel) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        if (uiState.eventAlreadyStarted) {
            FeedbackBanner(
                "This event has already started — location cannot be changed.",
                FeedbackTone.Error
            )
        }

        val readOnly = uiState.eventAlreadyStarted

        StepCard {
            FieldLabel("Primary venue", helper = "Enter the location name and its coordinates. Tip: find coords on maps.google.com.")
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(
                value = uiState.locationName,
                onValueChange = { if (!readOnly) viewModel.onLocationNameChange(it) },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Place name") },
                placeholder = { Text("e.g. Grand Arena, Istanbul") },
                singleLine = true,
                enabled = !readOnly,
                isError = uiState.locationError != null
            )
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = uiState.locationLat,
                    onValueChange = { if (!readOnly) viewModel.onLocationLatChange(it) },
                    modifier = Modifier.weight(1f),
                    label = { Text("Latitude") },
                    placeholder = { Text("41.0082") },
                    singleLine = true,
                    enabled = !readOnly,
                    isError = uiState.locationError != null,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal)
                )
                OutlinedTextField(
                    value = uiState.locationLng,
                    onValueChange = { if (!readOnly) viewModel.onLocationLngChange(it) },
                    modifier = Modifier.weight(1f),
                    label = { Text("Longitude") },
                    placeholder = { Text("28.9784") },
                    singleLine = true,
                    enabled = !readOnly,
                    isError = uiState.locationError != null,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal)
                )
            }
            uiState.locationError?.let { Spacer(Modifier.height(4.dp)); Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }

            if (uiState.locationLat.isNotBlank() && uiState.locationLng.isNotBlank()) {
                Spacer(Modifier.height(10.dp))
                Surface(shape = RoundedCornerShape(8.dp), color = Color(0xFFF0EDE9)) {
                    Text(
                        "📍 ${uiState.locationName.ifBlank { "Location" }} — ${uiState.locationLat}, ${uiState.locationLng}",
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                        style = MaterialTheme.typography.bodySmall,
                        color = BrandDark,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }
    }
}

// ── Step 3: Media ─────────────────────────────────────────────────────────────

@Composable
private fun MediaStep(
    uiState: CreateEventUiState,
    viewModel: CreateEventViewModel,
    context: android.content.Context,
    imagePickerLauncher: androidx.activity.result.ActivityResultLauncher<String>
) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        // Upload area
        StepCard {
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surface,
                border = BorderStroke(1.5.dp, Color(0xFFD1C9C3)),
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(enabled = !uiState.isUploadingImages) { imagePickerLauncher.launch("image/*") }
            ) {
                Column(
                    modifier = Modifier.padding(32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    if (uiState.isUploadingImages) {
                        CircularProgressIndicator(color = BrandMid, modifier = Modifier.size(36.dp))
                        Spacer(Modifier.height(12.dp))
                        Text("Uploading images...", fontWeight = FontWeight.SemiBold, color = BrandDark)
                    } else {
                        Icon(Icons.Default.AddPhotoAlternate, null, modifier = Modifier.size(36.dp), tint = BrandMid)
                        Spacer(Modifier.height(12.dp))
                        Text("Tap to add images", fontWeight = FontWeight.SemiBold, color = BrandDark)
                        Text("JPEG, PNG, WebP supported", style = MaterialTheme.typography.bodySmall, color = Color(0xFF78716C))
                    }
                }
            }

            // Upload button if URIs selected
            if (uiState.selectedImageUris.isNotEmpty()) {
                Spacer(Modifier.height(10.dp))
                Button(
                    onClick = { viewModel.uploadImages(context) },
                    enabled = !uiState.isUploadingImages,
                    colors = ButtonDefaults.buttonColors(containerColor = BrandDark),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Upload ${uiState.selectedImageUris.size} selected image${if (uiState.selectedImageUris.size == 1) "" else "s"}")
                }
            }

            uiState.imageUploadError?.let { Spacer(Modifier.height(6.dp)); Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        }

        // Pending images (selected but not yet uploaded)
        if (uiState.selectedImageUris.isNotEmpty()) {
            StepCard {
                Text("Selected for upload", style = MaterialTheme.typography.labelMedium, color = Color(0xFF78716C))
                Spacer(Modifier.height(8.dp))
                Row(modifier = Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    uiState.selectedImageUris.forEach { uri ->
                        Box {
                            AsyncImage(
                                model = uri, contentDescription = null,
                                modifier = Modifier.size(80.dp).clip(RoundedCornerShape(8.dp)),
                                contentScale = ContentScale.Crop
                            )
                            IconButton(
                                onClick = { viewModel.removeImageUri(uri) },
                                modifier = Modifier.align(Alignment.TopEnd).size(24.dp).background(Color.Black.copy(0.5f), CircleShape)
                            ) {
                                Icon(Icons.Default.Close, null, modifier = Modifier.size(12.dp), tint = Color.White)
                            }
                        }
                    }
                }
            }
        }

        // Already uploaded images
        if (uiState.uploadedImages.isNotEmpty()) {
            StepCard {
                Text("${uiState.uploadedImages.size} image${if (uiState.uploadedImages.size == 1) "" else "s"} uploaded", style = MaterialTheme.typography.labelMedium, color = Color(0xFF78716C))
                Spacer(Modifier.height(8.dp))
                Row(modifier = Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    uiState.uploadedImages.forEachIndexed { index, img ->
                        Box {
                            AsyncImage(
                                model = img.image_url, contentDescription = null,
                                modifier = Modifier.size(90.dp).clip(RoundedCornerShape(8.dp)),
                                contentScale = ContentScale.Crop
                            )
                            if (index == 0) {
                                Surface(
                                    modifier = Modifier.align(Alignment.TopStart).padding(4.dp),
                                    shape = RoundedCornerShape(4.dp),
                                    color = Color(0xFF065F46)
                                ) {
                                    Text("Cover", modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp), color = Color.White, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// ── Step 4: Venue & accessibility ─────────────────────────────────────────────

@Composable
private fun VenueStep(uiState: CreateEventUiState, viewModel: CreateEventViewModel) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        StepCard {
            FieldLabel("Special requirements", helper = "Share any health, safety, or attendee notes people should know in advance.")
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = uiState.healthRequirements,
                onValueChange = viewModel::onHealthRequirementsChange,
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("Mask policy, allergens, dress code, or other important notes.") },
                minLines = 3,
                maxLines = 6
            )
        }

        StepCard {
            FieldLabel("Accessibility", helper = "Help attendees understand comfort at the venue.")
            Spacer(Modifier.height(10.dp))
            val items = listOf(
                "Wheelchair accessible" to (uiState.wheelchairAccess to viewModel::onWheelchairAccessChange),
                "Accessible restroom" to (uiState.accessibleRestroom to viewModel::onAccessibleRestroomChange),
                "Elevator available" to (uiState.elevatorAvailable to viewModel::onElevatorAvailableChange),
                "Seating available" to (uiState.seatingAvailable to viewModel::onSeatingAvailableChange),
                "Captions or sign support" to (uiState.captionsSupport to viewModel::onCaptionsSupportChange),
                "Quiet-friendly environment" to (uiState.quietFriendly to viewModel::onQuietFriendlyChange),
            )
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items.forEach { (label, pair) ->
                    val (checked, setter) = pair
                    Surface(
                        shape = RoundedCornerShape(10.dp),
                        color = if (checked) BrandDark.copy(alpha = 0.06f) else MaterialTheme.colorScheme.surface,
                        border = BorderStroke(1.dp, if (checked) BrandMid.copy(0.5f) else Color(0xFFE0DAD6))
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { setter(!checked) }
                                .padding(horizontal = 14.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(label, style = MaterialTheme.typography.bodyMedium, fontWeight = if (checked) FontWeight.Medium else FontWeight.Normal)
                            Checkbox(
                                checked = checked,
                                onCheckedChange = setter,
                                colors = CheckboxDefaults.colors(checkedColor = BrandDark)
                            )
                        }
                    }
                }
            }
        }
    }
}

// ── Step 5: Settings ──────────────────────────────────────────────────────────

@Composable
private fun SettingsStep(uiState: CreateEventUiState, viewModel: CreateEventViewModel) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        if (!uiState.isEditMode && !uiState.settingsConfirmed) {
            FeedbackBanner("Review the visibility and capacity settings, then press Next to confirm.", FeedbackTone.Info)
        }

        // Visibility toggle
        StepCard {
            FieldLabel("Visibility")
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("public" to Icons.Default.Language, "private" to Icons.Default.Lock).forEach { (opt, icon) ->
                    val selected = uiState.visibility == opt
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = if (selected) BrandDark else MaterialTheme.colorScheme.surface,
                        border = BorderStroke(1.dp, if (selected) BrandDark else Color(0xFFD1C9C3)),
                        modifier = Modifier.weight(1f).clickable { viewModel.onVisibilityChange(opt) }
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                                Icon(icon, null, tint = if (selected) Color.White else BrandMid, modifier = Modifier.size(20.dp))
                                if (selected) Icon(Icons.Default.Check, null, tint = Color.White, modifier = Modifier.size(16.dp))
                            }
                            Spacer(Modifier.height(8.dp))
                            Text(opt.replaceFirstChar { it.uppercase() }, fontWeight = FontWeight.SemiBold, color = if (selected) Color.White else BrandDark)
                            Text(
                                if (opt == "public") "Anyone can discover and view." else "Only approved users can view.",
                                style = MaterialTheme.typography.bodySmall,
                                color = if (selected) Color.White.copy(0.8f) else Color(0xFF78716C)
                            )
                        }
                    }
                }
            }
        }

        // 18+ toggle
        StepCard {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text("18+ Age Restriction", fontWeight = FontWeight.Medium)
                    Text("Only users 18+ can view full details.", style = MaterialTheme.typography.bodySmall, color = Color(0xFF78716C))
                }
                Switch(checked = uiState.isAgeRestricted, onCheckedChange = viewModel::onAgeRestrictedChange,
                    colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = BrandDark))
            }
        }

        // Attendee limit
        StepCard {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text("Set attendee limit", fontWeight = FontWeight.Medium)
                    Text("Enable to show limited capacity.", style = MaterialTheme.typography.bodySmall, color = Color(0xFF78716C))
                }
                Switch(checked = uiState.attendeeLimitEnabled, onCheckedChange = viewModel::onAttendeeLimitEnabledChange,
                    colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = BrandDark))
            }
            if (uiState.attendeeLimitEnabled) {
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(
                    value = uiState.attendeeLimit,
                    onValueChange = viewModel::onAttendeeLimitChange,
                    modifier = Modifier.fillMaxWidth(0.5f),
                    label = { Text("Max attendees") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                )
            }
        }
    }
}

// ── Step 6: Review & Publish ──────────────────────────────────────────────────

@Composable
private fun ReviewStep(uiState: CreateEventUiState, viewModel: CreateEventViewModel) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {

        // Missing steps banner — shown when publish was attempted with incomplete steps
        if (uiState.missingSteps.isNotEmpty()) {
            Surface(
                shape = RoundedCornerShape(10.dp),
                color = FeedbackErrorBg,
                border = BorderStroke(1.dp, FeedbackErrorFg.copy(alpha = 0.25f))
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        "Complete the following steps before publishing:",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = FeedbackErrorFg
                    )
                    uiState.missingSteps.forEach { stepIndex ->
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(8.dp))
                                .clickable { viewModel.goToStep(stepIndex) }
                                .padding(vertical = 6.dp, horizontal = 4.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(24.dp)
                                    .clip(CircleShape)
                                    .background(FeedbackErrorFg),
                                contentAlignment = Alignment.Center
                            ) {
                                Text("${stepIndex + 1}", color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            }
                            Text(
                                EVENT_EDITOR_STEPS[stepIndex],
                                style = MaterialTheme.typography.bodyMedium,
                                color = FeedbackErrorFg,
                                fontWeight = FontWeight.Medium
                            )
                            Spacer(Modifier.weight(1f))
                            Text("Fix →", style = MaterialTheme.typography.bodySmall, color = FeedbackErrorFg)
                        }
                    }
                }
            }
        }

        ReviewCard(title = "Basics", onEdit = { viewModel.goToStep(0) },
            isComplete = uiState.stepCompleted(0)) {
            Text(uiState.title.ifBlank { "Untitled event" }, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.bodyLarge)
            Spacer(Modifier.height(8.dp))
            Row(modifier = Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                val cats = uiState.availableCategories.filter { it.id in uiState.selectedCategoryIds }
                if (cats.isEmpty()) Chip("No categories") else cats.forEach { Chip(it.name) }
            }
            if (uiState.description.isNotBlank()) {
                Spacer(Modifier.height(8.dp))
                Text(uiState.description, style = MaterialTheme.typography.bodySmall, color = Color(0xFF78716C), maxLines = 3, overflow = TextOverflow.Ellipsis)
            }
        }

        ReviewCard(title = "Schedule", onEdit = { viewModel.goToStep(1) },
            isComplete = uiState.stepCompleted(1)) {
            Text("${uiState.startDate} ${uiState.startTime} → ${uiState.endDate} ${uiState.endTime}", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
        }

        ReviewCard(title = "Location", onEdit = { viewModel.goToStep(2) },
            isComplete = uiState.stepCompleted(2)) {
            Text(uiState.locationName.ifBlank { "No location" }, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
            if (uiState.locationLat.isNotBlank()) Text("${uiState.locationLat}, ${uiState.locationLng}", style = MaterialTheme.typography.bodySmall, color = Color(0xFF78716C))
        }

        ReviewCard(title = "Media", onEdit = { viewModel.goToStep(3) },
            isComplete = uiState.uploadedImages.isNotEmpty()) {
            val count = uiState.uploadedImages.size
            Text(if (count > 0) "$count image${if (count == 1) "" else "s"} uploaded" else "No images uploaded (optional)", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
        }

        ReviewCard(title = "Settings", onEdit = { viewModel.goToStep(5) },
            isComplete = uiState.stepCompleted(5)) {
            Text(
                buildString {
                    append(uiState.visibility.replaceFirstChar { it.uppercase() })
                    if (uiState.isAgeRestricted) append(" · 18+")
                    if (uiState.attendeeLimitEnabled && uiState.attendeeLimit.isNotBlank()) append(" · Max ${uiState.attendeeLimit}")
                },
                style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium
            )
        }
    }
}

@Composable
private fun ReviewCard(
    title: String,
    onEdit: () -> Unit,
    isComplete: Boolean = true,
    content: @Composable ColumnScope.() -> Unit
) {
    Card(
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
        border = BorderStroke(1.dp, if (isComplete) Color(0xFFE8E3DF) else FeedbackErrorFg.copy(alpha = 0.4f))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    // Completion indicator
                    Box(
                        modifier = Modifier
                            .size(20.dp)
                            .clip(CircleShape)
                            .background(if (isComplete) StepDone else FeedbackErrorFg),
                        contentAlignment = Alignment.Center
                    ) {
                        if (isComplete) {
                            Icon(Icons.Default.Check, null, tint = Color.White, modifier = Modifier.size(12.dp))
                        } else {
                            Text("!", color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                    Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, color = BrandDark)
                }
                TextButton(onClick = onEdit, contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp)) {
                    Text("Edit", fontSize = 13.sp, color = BrandMid)
                }
            }
            HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp), color = Color(0xFFF0EDE9))
            content()
        }
    }
}

@Composable
private fun Chip(text: String) {
    Surface(shape = RoundedCornerShape(50), color = Color(0xFFF0EDE9)) {
        Text(text, modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp), fontSize = 12.sp, color = BrandDark)
    }
}

// ── Shared helpers ────────────────────────────────────────────────────────────

@Composable
private fun StepCard(content: @Composable ColumnScope.() -> Unit) {
    Card(
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
        border = BorderStroke(1.dp, Color(0xFFE8E3DF))
    ) {
        Column(modifier = Modifier.padding(16.dp), content = content)
    }
}

@Composable
private fun FieldLabel(text: String, helper: String? = null) {
    Text(text, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold)
    helper?.let { Spacer(Modifier.height(2.dp)); Text(it, style = MaterialTheme.typography.bodySmall, color = Color(0xFF78716C)) }
}

// ── Scrollbar ─────────────────────────────────────────────────────────────────

@Composable
private fun ScrollbarIndicator(scrollState: ScrollState, modifier: Modifier = Modifier, thumbWidth: Dp = 4.dp) {
    val thumbFraction = if (scrollState.maxValue > 0) scrollState.value.toFloat() / scrollState.maxValue.toFloat() else 0f
    Box(modifier = modifier.width(thumbWidth).drawWithContent {
        drawRoundRect(color = Color.Gray.copy(alpha = 0.12f), cornerRadius = CornerRadius(thumbWidth.toPx() / 2))
        val th = size.height * 0.15f
        drawRoundRect(color = BrandMid.copy(alpha = 0.5f), topLeft = Offset(0f, (size.height - th) * thumbFraction), size = Size(size.width, th), cornerRadius = CornerRadius(thumbWidth.toPx() / 2))
    })
}