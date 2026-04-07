package com.bounswe.group9.mobile.data.repository

import android.util.Log
import com.bounswe.group9.mobile.data.remote.LoginRequest
import com.bounswe.group9.mobile.data.remote.RefreshTokenRequest
import com.bounswe.group9.mobile.data.remote.RegisterRequest
import com.bounswe.group9.mobile.data.remote.RetrofitProvider
import com.bounswe.group9.mobile.data.remote.UserResponse
import org.json.JSONObject

data class AuthResult(val accessToken: String, val user: UserResponse)

private fun friendlyHttpError(code: Int, body: String): String {
    val detail = try {
        val json = JSONObject(body)
        when {
            json.has("detail") -> {
                val d = json.get("detail")
                if (d is String) d
                else {
                    // Pydantic validation array — pick first msg
                    val arr = json.getJSONArray("detail")
                    if (arr.length() > 0) arr.getJSONObject(0).optString("msg", "") else ""
                }
            }
            json.has("message") -> json.getString("message")
            else -> ""
        }
    } catch (_: Exception) { "" }

    return when {
        detail.isNotBlank() -> detail
        code == 401 -> "Incorrect email or password."
        code == 403 -> "Your account is not allowed to perform this action."
        code == 409 -> "An account with this email or username already exists."
        code == 422 -> "Please check your input and try again."
        code == 429 -> "Too many attempts. Please wait a moment and try again."
        else -> "Something went wrong (error $code). Please try again."
    }
}

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
            Result.failure(Exception(friendlyHttpError(e.code(), body)))
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
            Result.failure(Exception(friendlyHttpError(e.code(), body)))
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
            Result.failure(Exception(friendlyHttpError(e.code(), body)))
        } catch (e: Exception) {
            Log.e("AuthRepository", "Refresh failed: ${e.message}", e)
            Result.failure(e)
        }
    }
}
