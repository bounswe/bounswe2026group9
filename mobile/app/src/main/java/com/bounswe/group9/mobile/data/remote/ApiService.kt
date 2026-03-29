package com.bounswe.group9.mobile.data.remote

import retrofit2.http.Body
import retrofit2.http.POST

data class LoginRequest(
    val email: String,
    val password: String
)

data class RegisterRequest(
    val username: String,
    val email: String,
    val password: String,
    val date_of_birth: String
)

data class UserResponse(
    val id: String,
    val username: String,
    val email: String
)

data class AuthResponse(
    val user: UserResponse,
    val access_token: String,
    val token_type: String
)

interface ApiService {
    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): AuthResponse

    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequest): AuthResponse
}