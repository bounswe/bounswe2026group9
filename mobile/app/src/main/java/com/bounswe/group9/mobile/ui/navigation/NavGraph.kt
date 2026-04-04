package com.bounswe.group9.mobile.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.bounswe.group9.mobile.data.local.SessionManager
import com.bounswe.group9.mobile.ui.auth.AuthViewModel
import com.bounswe.group9.mobile.ui.auth.LoginScreen
import com.bounswe.group9.mobile.ui.discovery.DiscoveryScreen
import com.bounswe.group9.mobile.ui.discovery.DiscoveryViewModel

object Routes {
    const val LOGIN = "login"
    const val DISCOVERY = "discovery"
}

@Composable
fun AppNavGraph(
    navController: NavHostController,
    sessionManager: SessionManager,
    authViewModel: AuthViewModel,
    discoveryViewModel: DiscoveryViewModel
) {
    val token by sessionManager.tokenFlow.collectAsState(initial = null)
    val authState by authViewModel.uiState.collectAsState()

    // Always start at discovery — guests can browse, login is optional
    // If stored token exists, silently refresh on launch
    LaunchedEffect(Unit) {
        if (token != null) {
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
                onEventClick = { /* Event detail — Task #116 */ },
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
