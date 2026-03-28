package com.bounswe.group9.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.bounswe.group9.mobile.ui.auth.AuthViewModel
import com.bounswe.group9.mobile.ui.auth.LoginScreen
import com.bounswe.group9.mobile.ui.theme.EventAppMobileTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            EventAppMobileTheme {
                LoginScreen(viewModel = AuthViewModel())
            }
        }
    }
}