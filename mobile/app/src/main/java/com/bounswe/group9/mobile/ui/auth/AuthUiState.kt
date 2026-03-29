package com.bounswe.group9.mobile.ui.auth

data class AuthUiState(
    val username: String = "",
    val email: String = "",
    val password: String = "",
    val dateOfBirth: String = "",
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val isLoggedIn: Boolean = false
)