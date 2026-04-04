package com.bounswe.group9.mobile.ui.common

import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

fun formatEventDate(dateStr: String): String {
    return try {
        val formats = listOf(
            "yyyy-MM-dd'T'HH:mm:ssXXX",
            "yyyy-MM-dd'T'HH:mm:ss.SSSXXX",
            "yyyy-MM-dd'T'HH:mm:ssZ",
            "yyyy-MM-dd'T'HH:mm:ss"
        )
        var date: java.util.Date? = null
        for (fmt in formats) {
            try {
                val sdf = SimpleDateFormat(fmt, Locale.ENGLISH)
                sdf.timeZone = TimeZone.getTimeZone("UTC")
                date = sdf.parse(dateStr)
                break
            } catch (_: Exception) {}
        }
        date?.let { SimpleDateFormat("EEE, MMM d · HH:mm", Locale.ENGLISH).format(it) } ?: dateStr
    } catch (_: Exception) {
        dateStr
    }
}
