package com.bounswe.group9.mobile.data.repository

import android.util.Log
import com.bounswe.group9.mobile.data.remote.LoginRequest
import com.bounswe.group9.mobile.data.remote.RefreshTokenRequest
import com.bounswe.group9.mobile.data.remote.RegisterRequest
import com.bounswe.group9.mobile.data.remote.RetrofitProvider
import com.bounswe.group9.mobile.data.remote.UserResponse

data class AuthResult(val accessToken: String, val user: UserResponse)

class AuthRepository {

    suspend fun login(email: String, password: String): Result<AuthResult> {
        return try {
            val response = RetrofitProvider.apiService.login(
                LoginRequest(email = email.trim(), password = password.trim())
            )
            Result.success(AuthResult(response.access_token, response.user))
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("AuthRepository", "Login HTTP ${e.code()}: $body")
            Result.failure(Exception("${e.code()}: $body"))
        } catch (e: Exception) {
            Log.e("AuthRepository", "Login failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun register(
        username: String,
        email: String,
        password: String,
        dateOfBirth: String
    ): Result<AuthResult> {
        return try {
            val response = RetrofitProvider.apiService.register(
                RegisterRequest(
                    username = username.trim(),
                    email = email.trim(),
                    password = password.trim(),
                    date_of_birth = dateOfBirth.trim()
                )
            )
            Result.success(AuthResult(response.access_token, response.user))
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("AuthRepository", "Register HTTP ${e.code()}: $body")
            Result.failure(Exception("${e.code()}: $body"))
        } catch (e: Exception) {
            Log.e("AuthRepository", "Register failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun refreshToken(refreshToken: String?): Result<AuthResult> {
        return try {
            val response = RetrofitProvider.apiService.refresh(
                RefreshTokenRequest(refresh_token = refreshToken)
            )
            Result.success(AuthResult(response.access_token, response.user))
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("AuthRepository", "Refresh HTTP ${e.code()}: $body")
            Result.failure(Exception("${e.code()}: $body"))
        } catch (e: Exception) {
            Log.e("AuthRepository", "Refresh failed: ${e.message}", e)
            Result.failure(e)
        }
    }
}
