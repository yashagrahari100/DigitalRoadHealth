package com.roadhealth.app.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val DarkColorScheme = darkColorScheme(
    primary = Cyan500,
    secondary = Cyan600,
    tertiary = Green500,
    background = Dark900,
    surface = Dark700,
    onPrimary = Gray100,
    onSecondary = Gray100,
    onTertiary = Gray100,
    onBackground = Gray100,
    onSurface = Gray100,
    error = Red500
)

@Composable
fun DigitalRoadHealthTheme(
    content: @Composable () -> Unit
) {
    // Always use dark theme to match our dashboard aesthetic
    MaterialTheme(
        colorScheme = DarkColorScheme,
        typography = Typography,
        content = content
    )
}