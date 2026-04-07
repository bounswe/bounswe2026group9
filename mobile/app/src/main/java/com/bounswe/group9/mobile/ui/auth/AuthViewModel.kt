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
        val s = _uiState.value
        val validationError = when {
            s.email.isBlank()    -> "Email is required."
            s.password.isBlank() -> "Password is required."
            else -> null
        }
        if (validationError != null) {
            _uiState.value = s.copy(errorMessage = validationError)
            return
        }
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
                    sessionManager.saveUserId(auth.user.id)
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
        val s = _uiState.value
        val validationError = when {
            s.username.isBlank()     -> "Username is required."
            s.username.length < 3    -> "Username must be at least 3 characters."
            s.email.isBlank()        -> "Email is required."
            s.password.isBlank()     -> "Password is required."
            s.password.length < 8    -> "Password must be at least 8 characters."
            s.dateOfBirth.isBlank()  -> "Date of birth is required."
            !Regex("""\d{4}-\d{2}-\d{2}""").matches(s.dateOfBirth) ->
                "Date of birth must be in YYYY-MM-DD format."
            else -> null
        }
        if (validationError != null) {
            _uiState.value = s.copy(errorMessage = validationError)
            return
        }
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
                    sessionManager.saveUserId(auth.user.id)
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
                    sessionManager.saveUsername(auth.user.username)
                    sessionManager.saveUserId(auth.user.id)
                    _uiState.value = _uiState.value.copy(
                        isLoggedIn = true,
                        username = auth.user.username
                    )
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
