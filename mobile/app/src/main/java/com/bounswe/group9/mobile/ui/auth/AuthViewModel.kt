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

    fun onUsernameChange(v: String)    { _uiState.value = _uiState.value.copy(username = v) }
    fun onEmailChange(v: String)       { _uiState.value = _uiState.value.copy(email = v) }
    fun onPasswordChange(v: String)    { _uiState.value = _uiState.value.copy(password = v) }
    fun onDateOfBirthChange(v: String) { _uiState.value = _uiState.value.copy(dateOfBirth = v) }

    fun login() {
        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
        viewModelScope.launch {
            val result = repository.login(
                email = _uiState.value.email,
                password = _uiState.value.password
            )
            result.fold(
                onSuccess = { token ->
                    sessionManager.saveToken(token)
                    _uiState.value = _uiState.value.copy(isLoading = false, isLoggedIn = true)
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = e.message)
                }
            )
        }
    }

    fun register() {
        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
        viewModelScope.launch {
            val result = repository.register(
                username = _uiState.value.username,
                email = _uiState.value.email,
                password = _uiState.value.password,
                dateOfBirth = _uiState.value.dateOfBirth
            )
            result.fold(
                onSuccess = { token ->
                    sessionManager.saveToken(token)
                    _uiState.value = _uiState.value.copy(isLoading = false, isLoggedIn = true)
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = e.message)
                }
            )
        }
    }

    fun logout() {
        viewModelScope.launch {
            sessionManager.clearToken()
            _uiState.value = AuthUiState()
        }
    }
}
