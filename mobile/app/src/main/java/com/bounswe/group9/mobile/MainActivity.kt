package com.bounswe.group9.mobile

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.navigation.NavController
import androidx.navigation.compose.rememberNavController
import com.bounswe.group9.mobile.data.local.SessionManager
import com.bounswe.group9.mobile.ui.auth.AuthViewModel
import com.bounswe.group9.mobile.ui.discovery.DiscoveryViewModel
import com.bounswe.group9.mobile.ui.navigation.AppNavGraph
import com.bounswe.group9.mobile.ui.notifications.NotificationViewModel
import com.bounswe.group9.mobile.ui.profile.ProfileViewModel
import com.bounswe.group9.mobile.ui.theme.EventAppMobileTheme

class MainActivity : ComponentActivity() {

    private var navController: NavController? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val sessionManager = SessionManager(applicationContext)
        val authViewModel = AuthViewModel(sessionManager = sessionManager)
        val discoveryViewModel = DiscoveryViewModel()
        val notificationViewModel = NotificationViewModel()
        val profileViewModel = ProfileViewModel()

        setContent {
            EventAppMobileTheme {
                val nc = rememberNavController()
                navController = nc
                AppNavGraph(
                    navController = nc,
                    sessionManager = sessionManager,
                    authViewModel = authViewModel,
                    discoveryViewModel = discoveryViewModel,
                    notificationViewModel = notificationViewModel,
                    profileViewModel = profileViewModel
                )
            }
        }
    }

    /** Called when app is already running and a new deep link intent arrives. */
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        navController?.handleDeepLink(intent)
    }
}
