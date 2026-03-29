package com.bounswe.group9.mobile.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bounswe.group9.mobile.data.local.SessionManager
import com.bounswe.group9.mobile.data.repository.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class AuthViewModel(
    private val repository: AuthRepository = AuthRepository(),
    private val sessionManager: SessionManager
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            sessionManager.tokenFlow.collect { token ->
                if (!token.isNullOrBlank()) {
                    _uiState.value = _uiState.value.copy(isLoggedIn = true)
                }
            }
        }
    }

    fun onUsernameChange(newUsername: String) {
        _uiState.value = _uiState.value.copy(username = newUsername)
    }

    fun onEmailChange(newEmail: String) {
        _uiState.value = _uiState.value.copy(email = newEmail)
    }

    fun onPasswordChange(newPassword: String) {
        _uiState.value = _uiState.value.copy(password = newPassword)
    }

    fun onDateOfBirthChange(newDateOfBirth: String) {
        _uiState.value = _uiState.value.copy(dateOfBirth = newDateOfBirth)
    }

    fun login() {
        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)

        viewModelScope.launch {
            val token = repository.login(
                email = _uiState.value.email,
                password = _uiState.value.password
            )

            _uiState.value = if (token != null) {
                sessionManager.saveToken(token)
                _uiState.value.copy(
                    isLoading = false,
                    errorMessage = null,
                    isLoggedIn = true
                )
            } else {
                _uiState.value.copy(
                    isLoading = false,
                    errorMessage = "Login failed",
                    isLoggedIn = false
                )
            }
        }
    }

    fun register() {
        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)

        viewModelScope.launch {
            val token = repository.register(
                username = _uiState.value.username,
                email = _uiState.value.email,
                password = _uiState.value.password,
                dateOfBirth = _uiState.value.dateOfBirth
            )

            _uiState.value = if (token != null) {
                sessionManager.saveToken(token)
                _uiState.value.copy(
                    isLoading = false,
                    errorMessage = null,
                    isLoggedIn = true
                )
            } else {
                _uiState.value.copy(
                    isLoading = false,
                    errorMessage = "Registration failed",
                    isLoggedIn = false
                )
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            sessionManager.clearToken()
            _uiState.value = AuthUiState()
        }
    }
}