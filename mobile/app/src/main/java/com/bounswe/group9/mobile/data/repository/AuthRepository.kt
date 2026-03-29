package com.bounswe.group9.mobile.data.repository

import com.bounswe.group9.mobile.data.remote.LoginRequest
import com.bounswe.group9.mobile.data.remote.RegisterRequest
import com.bounswe.group9.mobile.data.remote.RetrofitProvider

class AuthRepository {

    suspend fun login(email: String, password: String): String? {
        return try {
            val response = RetrofitProvider.apiService.login(
                LoginRequest(email = email.trim(), password = password.trim())
            )
            response.access_token
        } catch (e: Exception) {
            null
        }
    }

    suspend fun register(
        username: String,
        email: String,
        password: String,
        dateOfBirth: String
    ): String? {
        return try {
            val response = RetrofitProvider.apiService.register(
                RegisterRequest(
                    username = username.trim(),
                    email = email.trim(),
                    password = password.trim(),
                    date_of_birth = dateOfBirth.trim()
                )
            )
            response.access_token
        } catch (e: Exception) {
            null
        }
    }
}