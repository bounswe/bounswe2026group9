package com.bounswe.group9.mobile.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.bounswe.group9.mobile.data.local.SessionManager
import com.bounswe.group9.mobile.ui.auth.AuthViewModel
import com.bounswe.group9.mobile.ui.auth.LoginScreen
import com.bounswe.group9.mobile.ui.discovery.DiscoveryScreen
import com.bounswe.group9.mobile.ui.discovery.DiscoveryViewModel
import com.bounswe.group9.mobile.ui.eventdetail.EventDetailScreen
import com.bounswe.group9.mobile.ui.eventdetail.EventDetailViewModel

object Routes {
    const val LOGIN = "login"
    const val DISCOVERY = "discovery"
    const val EVENT_DETAIL = "eventDetail/{eventId}"
    fun eventDetail(eventId: String) = "eventDetail/$eventId"
}

@Composable
fun AppNavGraph(
    navController: NavHostController,
    sessionManager: SessionManager,
    authViewModel: AuthViewModel,
    discoveryViewModel: DiscoveryViewModel
) {
    val token by sessionManager.tokenFlow.collectAsState(initial = null)
    val userId by sessionManager.userIdFlow.collectAsState(initial = null)
    val authState by authViewModel.uiState.collectAsState()

    // Silently refresh session when a stored token is first observed on cold start
    var hasAttemptedRefresh by remember { mutableStateOf(false) }
    LaunchedEffect(token) {
        if (token != null && !hasAttemptedRefresh) {
            hasAttemptedRefresh = true
            authViewModel.refreshSession(onExpired = {
                // Token expired — stay on discovery as guest, no redirect to login
            })
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
                username = authState.username.ifBlank { null }
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
    }
}
