package com.bounswe.group9.mobile.data.repository

import android.util.Log
import com.bounswe.group9.mobile.data.remote.BookmarkListResponseDto
import com.bounswe.group9.mobile.data.remote.HostProfileDto
import com.bounswe.group9.mobile.data.remote.MyProfileDto
import com.bounswe.group9.mobile.data.remote.ProfileUpdateRequestDto
import com.bounswe.group9.mobile.data.remote.RatingRequest
import com.bounswe.group9.mobile.data.remote.RetrofitProvider
import com.google.gson.Gson

class ProfileRepository {

    suspend fun getHostProfile(token: String?, userId: String): Result<HostProfileDto> {
        return try {
            val authHeader = token?.let { "Bearer $it" }
            val profile = RetrofitProvider.apiService.getHostProfile(userId, authHeader)
            Result.success(profile)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("ProfileRepository", "getHostProfile HTTP ${e.code()}: $body")
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("ProfileRepository", "getHostProfile failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun getMe(token: String): Result<MyProfileDto> {
        return try {
            val result = RetrofitProvider.apiService.getMe("Bearer $token")
            Result.success(result)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("ProfileRepository", "getMe HTTP ${e.code()}: $body")
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("ProfileRepository", "getMe failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun updateProfile(token: String, request: ProfileUpdateRequestDto): Result<MyProfileDto> {
        return try {
            val result = RetrofitProvider.apiService.updateMyProfile("Bearer $token", request)
            Result.success(result)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("ProfileRepository", "updateProfile HTTP ${e.code()}: $body")
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("ProfileRepository", "updateProfile failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun getBookmarks(token: String, page: Int = 1, pageSize: Int = 20): Result<BookmarkListResponseDto> {
        return try {
            val result = RetrofitProvider.apiService.getMyBookmarks("Bearer $token", page, pageSize)
            Result.success(result)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("ProfileRepository", "getBookmarks HTTP ${e.code()}: $body")
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("ProfileRepository", "getBookmarks failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    suspend fun rateHost(token: String, hostId: String, score: Double): Result<Unit> {
        return try {
            RetrofitProvider.apiService.rateHost(hostId, "Bearer $token", RatingRequest(score))
            Result.success(Unit)
        } catch (e: retrofit2.HttpException) {
            val body = e.response()?.errorBody()?.string() ?: "Unknown error"
            Log.e("ProfileRepository", "rateHost HTTP ${e.code()}: $body")
            Result.failure(Exception(parseErrorMessage(body, e.code())))
        } catch (e: Exception) {
            Log.e("ProfileRepository", "rateHost failed: ${e.message}", e)
            Result.failure(e)
        }
    }
}

private fun parseErrorMessage(body: String, code: Int): String {
    return try {
        val json = Gson().fromJson(body, com.google.gson.JsonObject::class.java)
        json.get("detail")?.asString ?: "Error $code"
    } catch (_: Exception) {
        "Error $code"
    }
}
