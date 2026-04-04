package com.bounswe.group9.mobile.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColorScheme = lightColorScheme(
    primary          = BrandDark,
    onPrimary        = White,
    secondary        = BrandSurfaceLight,
    onSecondary      = BrandDark,
    tertiary         = BrandMid,
    onTertiary       = White,
    background       = BrandBgLight,
    onBackground     = BrandDark,
    surface          = BrandSurfaceLight,
    onSurface        = BrandDark,
    surfaceVariant   = BrandBgLight,
    onSurfaceVariant = MutedLight,
    error            = Destructive,
    onError          = White,
    outline          = BrandMid,
)

private val DarkColorScheme = darkColorScheme(
    primary          = BrandSurfaceLight,
    onPrimary        = BrandDark,
    secondary        = BrandSurfaceDark,
    onSecondary      = BrandFgDark,
    tertiary         = BrandMid,
    onTertiary       = White,
    background       = BrandBgDark,
    onBackground     = BrandFgDark,
    surface          = BrandSurfaceDark,
    onSurface        = BrandFgDark,
    surfaceVariant   = BrandBgDark,
    onSurfaceVariant = MutedDark,
    error            = Destructive,
    onError          = White,
    outline          = BrandMid,
)

@Composable
fun EventAppMobileTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme,
        typography = Typography,
        content = content
    )
}
