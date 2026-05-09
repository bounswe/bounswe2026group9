package com.bounswe.group9.mobile.ui.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import kotlinx.coroutines.delay
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import androidx.navigation.navDeepLink
import com.bounswe.group9.mobile.data.local.SessionManager
import com.bounswe.group9.mobile.ui.auth.AuthViewModel
import com.bounswe.group9.mobile.ui.auth.LoginScreen
import com.bounswe.group9.mobile.ui.checkin.HostAttendeeListScreen
import com.bounswe.group9.mobile.ui.checkin.HostScanScreen
import com.bounswe.group9.mobile.ui.createevent.CreateEventScreen
import com.bounswe.group9.mobile.ui.createevent.CreateEventViewModel
import com.bounswe.group9.mobile.ui.discovery.DiscoveryScreen
import com.bounswe.group9.mobile.ui.discovery.DiscoveryViewModel
import com.bounswe.group9.mobile.ui.eventdetail.EventDetailScreen
import com.bounswe.group9.mobile.ui.eventdetail.EventDetailViewModel
import com.bounswe.group9.mobile.ui.hostprofile.HostProfileScreen
import com.bounswe.group9.mobile.ui.hostprofile.HostProfileViewModel
import com.bounswe.group9.mobile.ui.invite.InviteAcceptScreen
import com.bounswe.group9.mobile.ui.invite.InviteAcceptViewModel
import com.bounswe.group9.mobile.ui.notifications.NotificationScreen
import com.bounswe.group9.mobile.ui.notifications.NotificationViewModel
import com.bounswe.group9.mobile.ui.profile.ProfileScreen
import com.bounswe.group9.mobile.ui.profile.ProfileViewModel

object Routes {
    const val LOGIN = "login"
    const val DISCOVERY = "discovery"
    const val NOTIFICATIONS = "notifications"
    const val PROFILE = "profile"
    const val EVENT_DETAIL = "eventDetail/{eventId}"
    const val HOST_PROFILE = "hostProfile/{userId}"
    const val INVITE_ACCEPT = "inviteAccept/{eventId}/{inviteToken}"
    const val CREATE_EVENT = "createEvent"
    const val EDIT_EVENT = "editEvent/{eventId}"
    const val HOST_SCAN = "hostScan/{eventId}"
    const val HOST_ATTENDEES = "hostAttendees/{eventId}"
    fun eventDetail(eventId: String) = "eventDetail/$eventId"
    fun hostProfile(userId: String) = "hostProfile/$userId"
    fun inviteAccept(eventId: String, inviteToken: String) = "inviteAccept/$eventId/$inviteToken"
    fun editEvent(eventId: String) = "editEvent/$eventId"
    fun hostScan(eventId: String) = "hostScan/$eventId"
    fun hostAttendees(eventId: String) = "hostAttendees/$eventId"
}

@Composable
fun AppNavGraph(
    navController: NavHostController,
    sessionManager: SessionManager,
    authViewModel: AuthViewModel,
    discoveryViewModel: DiscoveryViewModel,
    notificationViewModel: NotificationViewModel,
    profileViewModel: ProfileViewModel
) {
    val token by sessionManager.tokenFlow.collectAsState(initial = null)
    val userId by sessionManager.userIdFlow.collectAsState(initial = null)
    val authState by authViewModel.uiState.collectAsState()
    val notificationState by notificationViewModel.uiState.collectAsState()

    // Silently refresh session when a stored token is first observed on cold start
    var hasAttemptedRefresh by remember { mutableStateOf(false) }
    LaunchedEffect(token) {
        if (token != null && !hasAttemptedRefresh) {
            hasAttemptedRefresh = true
            authViewModel.refreshSession(onExpired = {
                // Token expired — stay on discovery as guest, no redirect to login
            })
        }
        // Keep notification unread count in sync whenever token changes
        notificationViewModel.setToken(token)
    }

    // Sync profile credentials (token + userId) together
    LaunchedEffect(token, userId) {
        profileViewModel.setCredentials(token, userId)
    }

    // Poll unread count every 60s while the user is authenticated
    LaunchedEffect(token) {
        while (token != null) {
            delay(60_000)
            notificationViewModel.refresh()
        }
    }

    NavHost(navController = navController, startDestination = Routes.DISCOVERY) {
        composable(Routes.DISCOVERY) {
            DiscoveryScreen(
                viewModel = discoveryViewModel,
                token = token,
                onEventClick = { eventId ->
                    navController.navigate(Routes.eventDetail(eventId))
                },
                onLoginClick = {
                    navController.navigate(Routes.LOGIN)
                },
                onLogout = {
                    authViewModel.logout()
                    // Stay on discovery as guest after logout
                },
                username = authState.username.ifBlank { null },
                unreadNotificationCount = notificationState.unreadCount,
                onNotificationsClick = {
                    navController.navigate(Routes.NOTIFICATIONS)
                },
                onProfileClick = {
                    navController.navigate(Routes.PROFILE)
                },
                onCreateEvent = {
                    navController.navigate(Routes.CREATE_EVENT)
                }
            )
        }
        composable(Routes.NOTIFICATIONS) {
            NotificationScreen(
                viewModel = notificationViewModel,
                token = token,
                onBack = { navController.popBackStack() },
                onEventClick = { eventId ->
                    navController.navigate(Routes.eventDetail(eventId))
                }
            )
        }
        composable(Routes.PROFILE) {
            ProfileScreen(
                viewModel = profileViewModel,
                token = token,
                username = authState.username.ifBlank { null },
                onBack = { navController.popBackStack() },
                onEventClick = { eventId ->
                    navController.navigate(Routes.eventDetail(eventId))
                }
            )
        }
        composable(
            route = Routes.EVENT_DETAIL,
            arguments = listOf(navArgument("eventId") { type = NavType.StringType })
        ) { backStackEntry ->
            val eventId = backStackEntry.arguments?.getString("eventId") ?: return@composable
            val detailViewModel = remember(eventId) { EventDetailViewModel() }
            EventDetailScreen(
                viewModel = detailViewModel,
                eventId = eventId,
                token = token,
                currentUserId = userId,
                onBack = {
                    navController.popBackStack()
                    discoveryViewModel.refresh() // Sync bookmark/going state
                },
                onNavigateToHost = { hostId ->
                    navController.navigate(Routes.hostProfile(hostId))
                },
                onNavigateToEvent = { targetEventId ->
                    navController.navigate(Routes.eventDetail(targetEventId))
                },
                onNavigateToEdit = { event ->
                    navController.navigate(Routes.editEvent(event.id))
                },
                onDeleteSuccess = {
                    navController.navigate(Routes.DISCOVERY) {
                        popUpTo(Routes.DISCOVERY) { inclusive = true }
                    }
                    discoveryViewModel.refresh()
                },
                onNavigateToScan = { id ->
                    navController.navigate(Routes.hostScan(id))
                },
                onNavigateToAttendees = { id ->
                    navController.navigate(Routes.hostAttendees(id))
                }
            )
        }
        composable(
            route = Routes.HOST_SCAN,
            arguments = listOf(navArgument("eventId") { type = NavType.StringType })
        ) { backStackEntry ->
            val scanEventId = backStackEntry.arguments?.getString("eventId") ?: return@composable
            HostScanScreen(
                eventId = scanEventId,
                authToken = token,
                onBack = { navController.popBackStack() },
                onOpenAttendeeList = {
                    navController.navigate(Routes.hostAttendees(scanEventId))
                }
            )
        }
        composable(
            route = Routes.HOST_ATTENDEES,
            arguments = listOf(navArgument("eventId") { type = NavType.StringType })
        ) { backStackEntry ->
            val rosterEventId = backStackEntry.arguments?.getString("eventId") ?: return@composable
            HostAttendeeListScreen(
                eventId = rosterEventId,
                authToken = token,
                onBack = { navController.popBackStack() },
                onNavigateToProfile = { profileUserId ->
                    navController.navigate(Routes.hostProfile(profileUserId))
                }
            )
        }
        composable(
            route = Routes.HOST_PROFILE,
            arguments = listOf(navArgument("userId") { type = NavType.StringType })
        ) { backStackEntry ->
            val profileUserId = backStackEntry.arguments?.getString("userId") ?: return@composable
            val profileViewModel = remember(profileUserId) { HostProfileViewModel() }
            HostProfileScreen(
                viewModel = profileViewModel,
                userId = profileUserId,
                token = token,
                currentUserId = userId,
                onBack = { navController.popBackStack() },
                onEventClick = { eventId ->
                    navController.navigate(Routes.eventDetail(eventId))
                },
                onNavigateToProfile = { raterId ->
                    navController.navigate(Routes.hostProfile(raterId))
                }
            )
        }
        composable(Routes.LOGIN) {
            LoginScreen(
                viewModel = authViewModel,
                onLoginSuccess = {
                    navController.popBackStack() // back to discovery
                }
            )
        }
        composable(Routes.CREATE_EVENT) {
            val createViewModel = remember { CreateEventViewModel() }
            CreateEventScreen(
                token = token,
                editEvent = null,
                onBack = { navController.popBackStack() },
                onEventSaved = { eventId ->
                    navController.navigate(Routes.eventDetail(eventId)) {
                        popUpTo(Routes.CREATE_EVENT) { inclusive = true }
                    }
                    discoveryViewModel.refresh()
                },
                viewModel = createViewModel
            )
        }
        composable(
            route = Routes.EDIT_EVENT,
            arguments = listOf(navArgument("eventId") { type = NavType.StringType })
        ) { backStackEntry ->
            val editEventId = backStackEntry.arguments?.getString("eventId") ?: return@composable
            val detailVm = remember(editEventId) { EventDetailViewModel() }
            val detailState by detailVm.uiState.collectAsState()
            LaunchedEffect(editEventId, token) {
                detailVm.loadEvent(editEventId, token)
            }
            val eventToEdit = detailState.fullDetail
            if (eventToEdit != null) {
                val editVm = remember(editEventId) { CreateEventViewModel() }
                CreateEventScreen(
                    token = token,
                    editEvent = eventToEdit,
                    onBack = { navController.popBackStack() },
                    onEventSaved = { savedId ->
                        navController.navigate(Routes.eventDetail(savedId)) {
                            popUpTo(Routes.EDIT_EVENT) { inclusive = true }
                        }
                        discoveryViewModel.refresh()
                    },
                    viewModel = editVm
                )
            } else {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = androidx.compose.ui.Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            }
        }
        composable(
            route = Routes.INVITE_ACCEPT,
            arguments = listOf(
                navArgument("eventId") { type = NavType.StringType },
                navArgument("inviteToken") { type = NavType.StringType }
            ),
            deepLinks = listOf(
                // sem://invite/{eventId}/{inviteToken}
                navDeepLink { uriPattern = "sem://invite/{eventId}/{inviteToken}" }
            )
        ) { backStackEntry ->
            val eventId = backStackEntry.arguments?.getString("eventId") ?: return@composable
            val inviteToken = backStackEntry.arguments?.getString("inviteToken") ?: return@composable
            val inviteViewModel = remember { InviteAcceptViewModel() }
            InviteAcceptScreen(
                viewModel = inviteViewModel,
                eventId = eventId,
                inviteToken = inviteToken,
                authToken = token,
                onNavigateToEvent = { id ->
                    navController.navigate(Routes.eventDetail(id)) {
                        popUpTo(Routes.DISCOVERY) // clear invite screen from back stack
                    }
                },
                onNavigateHome = {
                    navController.navigate(Routes.DISCOVERY) {
                        popUpTo(Routes.DISCOVERY) { inclusive = true }
                    }
                }
            )
        }
    }
}