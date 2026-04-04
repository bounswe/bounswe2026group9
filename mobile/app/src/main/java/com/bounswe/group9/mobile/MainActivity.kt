package com.bounswe.group9.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.navigation.compose.rememberNavController
import com.bounswe.group9.mobile.data.local.SessionManager
import com.bounswe.group9.mobile.ui.auth.AuthViewModel
import com.bounswe.group9.mobile.ui.discovery.DiscoveryViewModel
import com.bounswe.group9.mobile.ui.navigation.AppNavGraph
import com.bounswe.group9.mobile.ui.theme.EventAppMobileTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val sessionManager = SessionManager(applicationContext)
        val authViewModel = AuthViewModel(sessionManager = sessionManager)
        val discoveryViewModel = DiscoveryViewModel()

        setContent {
            EventAppMobileTheme {
                val navController = rememberNavController()
                AppNavGraph(
                    navController = navController,
                    sessionManager = sessionManager,
                    authViewModel = authViewModel,
                    discoveryViewModel = discoveryViewModel
                )
            }
        }
    }
}
