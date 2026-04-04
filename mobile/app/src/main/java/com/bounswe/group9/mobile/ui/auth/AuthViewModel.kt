package com.bounswe.group9.mobile.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bounswe.group9.mobile.data.local.SessionManager
import com.bounswe.group9.mobile.data.remote.RetrofitProvider
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
        // Restore session on launch
        viewModelScope.launch {
            sessionManager.tokenFlow.collect { token ->
                if (!token.isNullOrBlank()) {
                    _uiState.value = _uiState.value.copy(isLoggedIn = true)
                }
            }
        }
        viewModelScope.launch {
            sessionManager.usernameFlow.collect { username ->
                if (!username.isNullOrBlank()) {
                    _uiState.value = _uiState.value.copy(username = username)
                }
            }
        }
        // Save refresh token when cookie arrives
        RetrofitProvider.onRefreshCookieReceived = { refreshToken ->
            viewModelScope.launch {
                sessionManager.saveRefreshToken(refreshToken)
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
                onSuccess = { auth ->
                    sessionManager.saveToken(auth.accessToken)
                    sessionManager.saveUsername(auth.user.username)
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isLoggedIn = true,
                        username = auth.user.username
                    )
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
                onSuccess = { auth ->
                    sessionManager.saveToken(auth.accessToken)
                    sessionManager.saveUsername(auth.user.username)
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isLoggedIn = true,
                        username = auth.user.username
                    )
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(isLoading = false, errorMessage = e.message)
                }
            )
        }
    }

    fun refreshSession(onExpired: () -> Unit = {}) {
        viewModelScope.launch {
            val refreshToken = sessionManager.getRefreshToken()
            val result = repository.refreshToken(refreshToken)
            result.fold(
                onSuccess = { auth ->
                    sessionManager.saveToken(auth.accessToken)
                    _uiState.value = _uiState.value.copy(isLoggedIn = true)
                },
                onFailure = {
                    // Refresh token expired — force logout
                    logout()
                    onExpired()
                }
            )
        }
    }

    fun logout() {
        viewModelScope.launch {
            sessionManager.clearAll()
            _uiState.value = AuthUiState()
        }
    }
}
