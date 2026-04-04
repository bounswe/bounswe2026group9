package com.bounswe.group9.mobile.data.remote

import kotlinx.coroutines.runBlocking
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitProvider {

    const val BASE_URL = "https://thesocialeventmapper.social/"
    private const val REFRESH_COOKIE_NAME = "sem_refresh_token"

    // In-memory cookie store to capture refresh token cookie from Set-Cookie header
    private val cookieStore = mutableMapOf<String, List<Cookie>>()

    val cookieJar = object : CookieJar {
        override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
            cookieStore[url.host] = cookies
            // Also notify listener when refresh cookie arrives
            cookies.find { it.name == REFRESH_COOKIE_NAME }?.let { cookie ->
                onRefreshCookieReceived?.invoke(cookie.value)
            }
        }
        override fun loadForRequest(url: HttpUrl): List<Cookie> {
            return cookieStore[url.host] ?: emptyList()
        }
    }

    // Called when a new refresh token cookie is received
    var onRefreshCookieReceived: ((String) -> Unit)? = null

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val okHttpClient = OkHttpClient.Builder()
        .cookieJar(cookieJar)
        .addInterceptor(loggingInterceptor)
        .build()

    val apiService: ApiService = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(ApiService::class.java)
}
