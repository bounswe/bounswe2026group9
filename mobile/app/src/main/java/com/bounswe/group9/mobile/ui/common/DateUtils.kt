package com.bounswe.group9.mobile.ui.common

import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

/**
 * Parses an RFC 3339 / ISO 8601 datetime string from the backend and formats
 * it for display in the device's local timezone.
 *
 * The backend guarantees strings with a timezone offset (e.g. "+00:00" or "Z"),
 * so the primary parsers use the "XXX" pattern which reads the embedded offset
 * correctly. A bare datetime (no offset) is treated as UTC as a safe fallback.
 */
fun formatEventDate(dateStr: String): String {
    return try {
        // (format, treatAsUtcIfNoOffset)
        val formats = listOf(
            "yyyy-MM-dd'T'HH:mm:ssXXX"     to false,
            "yyyy-MM-dd'T'HH:mm:ss.SSSXXX" to false,
            "yyyy-MM-dd'T'HH:mm:ssZ"        to false,
            "yyyy-MM-dd'T'HH:mm:ss"         to true,   // no offset → assume UTC
        )
        var date: java.util.Date? = null
        for ((fmt, forceUtc) in formats) {
            try {
                val sdf = SimpleDateFormat(fmt, Locale.ENGLISH)
                // Only override timezone for naive (offset-less) patterns; for
                // offset-aware patterns the parser extracts the offset from the
                // string itself and setting a different timezone would corrupt it.
                if (forceUtc) {
                    sdf.timeZone = TimeZone.getTimeZone("UTC")
                }
                date = sdf.parse(dateStr)
                break
            } catch (_: Exception) {}
        }
        // Render in device local timezone so the user sees their local time.
        val displayFmt = SimpleDateFormat("EEE, MMM d · HH:mm", Locale.ENGLISH)
        displayFmt.timeZone = TimeZone.getDefault()
        date?.let { displayFmt.format(it) } ?: dateStr
    } catch (_: Exception) {
        dateStr
    }
}
