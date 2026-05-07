package com.bounswe.group9.mobile.data.remote

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.URL
import java.net.URLEncoder

data class NominatimResult(
    val displayName: String,
    val shortName: String,
    val lat: Double,
    val lng: Double
)

object NominatimClient {
    private const val BASE = "https://nominatim.openstreetmap.org"
    private const val UA = "SocialEventMapper/1.0"

    /** Search suggestions: text → up to [limit] results with coordinates. */
    suspend fun suggest(query: String, limit: Int = 5): List<NominatimResult> = withContext(Dispatchers.IO) {
        try {
            val encoded = URLEncoder.encode(query, "UTF-8")
            val url = "$BASE/search?q=$encoded&format=json&limit=$limit&addressdetails=1"
            val json = URL(url).openConnection().apply {
                setRequestProperty("User-Agent", UA)
                connectTimeout = 5000
                readTimeout = 5000
            }.getInputStream().bufferedReader().readText()
            val arr = JSONArray(json)
            (0 until arr.length()).mapNotNull { i ->
                val obj = arr.getJSONObject(i)
                val display = obj.optString("display_name").takeIf { it.isNotEmpty() } ?: return@mapNotNull null
                val short = buildShortName(obj)
                NominatimResult(
                    displayName = display,
                    shortName = short,
                    lat = obj.getDouble("lat"),
                    lng = obj.getDouble("lon")
                )
            }
        } catch (e: Exception) {
            Log.w("NominatimClient", "suggest failed: ${e.message}")
            emptyList()
        }
    }

    /** Forward geocode: text → (lat, lng) top result. Returns null on failure or no results. */
    suspend fun geocode(query: String): Pair<Double, Double>? = withContext(Dispatchers.IO) {
        try {
            val encoded = URLEncoder.encode(query, "UTF-8")
            val url = "$BASE/search?q=$encoded&format=json&limit=1"
            val json = URL(url).openConnection().apply {
                setRequestProperty("User-Agent", UA)
                connectTimeout = 5000
                readTimeout = 5000
            }.getInputStream().bufferedReader().readText()
            val arr = JSONArray(json)
            if (arr.length() == 0) return@withContext null
            val obj = arr.getJSONObject(0)
            Pair(obj.getDouble("lat"), obj.getDouble("lon"))
        } catch (e: Exception) {
            Log.w("NominatimClient", "geocode failed: ${e.message}")
            null
        }
    }

    /** Reverse geocode: (lat, lng) → human-readable address string. Returns null on failure. */
    suspend fun reverseGeocode(lat: Double, lng: Double): String? = withContext(Dispatchers.IO) {
        try {
            val url = "$BASE/reverse?lat=$lat&lon=$lng&format=json"
            val json = URL(url).openConnection().apply {
                setRequestProperty("User-Agent", UA)
                connectTimeout = 5000
                readTimeout = 5000
            }.getInputStream().bufferedReader().readText()
            val obj = JSONObject(json)
            val display = obj.optString("display_name").takeIf { it.isNotEmpty() } ?: return@withContext null
            val parts = display.split(",").take(3).joinToString(",").trim()
            if (parts.length > 100) parts.take(100) else parts
        } catch (e: Exception) {
            Log.w("NominatimClient", "reverseGeocode failed: ${e.message}")
            null
        }
    }

    private fun buildShortName(obj: JSONObject): String {
        val addr = obj.optJSONObject("address") ?: return obj.optString("display_name").split(",").first().trim()
        val venue = addr.optString("amenity").ifEmpty { null }
            ?: addr.optString("building").ifEmpty { null }
            ?: addr.optString("shop").ifEmpty { null }
            ?: addr.optString("tourism").ifEmpty { null }
        val area = addr.optString("neighbourhood").ifEmpty { null }
            ?: addr.optString("suburb").ifEmpty { null }
            ?: addr.optString("quarter").ifEmpty { null }
        val city = addr.optString("city").ifEmpty { null }
            ?: addr.optString("town").ifEmpty { null }
            ?: addr.optString("village").ifEmpty { null }
        return listOfNotNull(venue, area, city).take(2).joinToString(", ")
            .ifEmpty { obj.optString("display_name").split(",").first().trim() }
    }
}
