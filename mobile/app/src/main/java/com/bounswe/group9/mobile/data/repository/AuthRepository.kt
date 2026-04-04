package com.bounswe.group9.mobile.data.repository

import android.util.Log
import com.bounswe.group9.mobile.data.remote.LoginRequest
import com.bounswe.group9.mobile.data.remote.RegisterRequest
import com.bounswe.group9.mobile.data.remote.RetrofitProvider

class AuthRepository {

    suspend fun login(email: String, password: String): Result<String> {
        return try {
            val response = RetrofitProvider.apiService.login(
                LoginRequest(email = email.trim(), password = password.trim())
            )
            Result.success(response.access_token)
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
    ): Result<String> {
        return try {
            val response = RetrofitProvider.apiService.register(
                RegisterRequest(
                    username = username.trim(),
                    email = email.trim(),
                    password = password.trim(),
                    date_of_birth = dateOfBirth.trim()
                )
            )
            Result.success(response.access_token)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("AuthRepository", "Register HTTP ${e.code()}: $body")
            Result.failure(Exception("${e.code()}: $body"))
        } catch (e: Exception) {
            Log.e("AuthRepository", "Register failed: ${e.message}", e)
            Result.failure(e)
        }
    }
}
