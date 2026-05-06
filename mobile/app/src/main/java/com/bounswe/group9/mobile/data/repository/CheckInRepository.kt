package com.bounswe.group9.mobile.data.repository

import android.util.Log
import com.bounswe.group9.mobile.data.remote.AttendeeQrTokenDto
import com.bounswe.group9.mobile.data.remote.AttendeeStatusDto
import com.bounswe.group9.mobile.data.remote.CheckInRequest
import com.bounswe.group9.mobile.data.remote.CheckInResultDto
import com.bounswe.group9.mobile.data.remote.RetrofitProvider
import com.google.gson.Gson
import com.google.gson.JsonObject

/**
 * Host scanner check-in outcomes mapped from HTTP status codes.
 * The scan screen renders one inline message per case.
 */
sealed class CheckInOutcome {
    data class Success(val result: CheckInResultDto) : CheckInOutcome()
    object InvalidPayload : CheckInOutcome()        // 400 — tampered / wrong-event / expired
    object NotHost : CheckInOutcome()               // 403 — current user is not the host
    object NotGoing : CheckInOutcome()              // 404 — no attendance record
    object AlreadyCheckedIn : CheckInOutcome()      // 409 — duplicate scan
    data class Error(val message: String) : CheckInOutcome()  // 5xx / network
}

class CheckInRepository {

    /** Fetches the signed QR token for the authenticated Going user. */
    suspend fun getMyQr(token: String, eventId: String): Result<AttendeeQrTokenDto> {
        return try {
            val response = RetrofitProvider.apiService.getMyAttendeeQr(eventId, "Bearer $token")
            if (!response.isSuccessful) {
                val body = response.errorBody()?.string() ?: "Unknown error"
                Log.w("CheckInRepository", "getMyQr HTTP ${response.code()}: $body")
                return Result.failure(Exception(parseErrorMessage(body, response.code())))
            }
            val dto = response.body()
                ?: return Result.failure(Exception("Empty QR response"))
            Result.success(dto)
        } catch (e: Exception) {
            Log.e("CheckInRepository", "getMyQr failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    /** Submits a scanned QR payload as the host. Maps HTTP codes to a typed outcome. */
    suspend fun submitCheckIn(token: String, eventId: String, qrToken: String): CheckInOutcome =
        postCheckIn(token, eventId, CheckInRequest(token = qrToken))

    /** Manual fallback — host marks an attendee in by user_id without scanning. */
    suspend fun manualCheckIn(token: String, eventId: String, userId: String): CheckInOutcome =
        postCheckIn(token, eventId, CheckInRequest(user_id = userId))

    private suspend fun postCheckIn(token: String, eventId: String, requestBody: CheckInRequest): CheckInOutcome {
        return try {
            val response = RetrofitProvider.apiService.postCheckIn(
                eventId, "Bearer $token", requestBody
            )
            if (response.isSuccessful) {
                val payload = response.body()
                    ?: return CheckInOutcome.Error("Empty response")
                CheckInOutcome.Success(payload)
            } else {
                when (response.code()) {
                    400 -> CheckInOutcome.InvalidPayload
                    403 -> CheckInOutcome.NotHost
                    404 -> CheckInOutcome.NotGoing
                    409 -> CheckInOutcome.AlreadyCheckedIn
                    else -> {
                        val msg = response.errorBody()?.string()?.let { parseErrorMessage(it, response.code()) }
                            ?: "Error ${response.code()}"
                        CheckInOutcome.Error(msg)
                    }
                }
            }
        } catch (e: Exception) {
            Log.e("CheckInRepository", "submitCheckIn failed: ${e.message}", e)
            CheckInOutcome.Error(e.message ?: "Network error")
        }
    }

    /** Host-only roster of going attendees with check-in status. */
    suspend fun listAttendees(token: String, eventId: String): Result<List<AttendeeStatusDto>> {
        return try {
            val response = RetrofitProvider.apiService.getEventAttendees(eventId, "Bearer $token")
            if (!response.isSuccessful) {
                val body = response.errorBody()?.string() ?: "Unknown error"
                Log.w("CheckInRepository", "listAttendees HTTP ${response.code()}: $body")
                return Result.failure(Exception(parseErrorMessage(body, response.code())))
            }
            Result.success(response.body() ?: emptyList())
        } catch (e: Exception) {
            Log.e("CheckInRepository", "listAttendees failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    private fun parseErrorMessage(body: String, code: Int): String {
        return try {
            val json = Gson().fromJson(body, JsonObject::class.java)
            json.get("detail")?.asString ?: "Error $code"
        } catch (_: Exception) {
            "Error $code"
        }
    }
}
