package com.roadhealth.app.data

import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf

/**
 * Shared observable state between SensorService and the Compose UI.
 * This is a lightweight singleton — no disk I/O, no database.
 * The UI observes these mutable states and recomposes automatically.
 */
object ScannerState {

    // Live stats
    val totalAnomaliesDetected = mutableStateOf(0)
    val totalApiCallsSent = mutableStateOf(0)
    val totalApiErrors = mutableStateOf(0)
    val bufferSize = mutableStateOf(0)
    val currentJerk = mutableStateOf(0f)
    val currentLat = mutableStateOf(0.0)
    val currentLon = mutableStateOf(0.0)
    val isScanning = mutableStateOf(false)

    // Event log (most recent 50 events, newest first)
    data class LogEntry(
        val timestamp: Long = System.currentTimeMillis(),
        val type: LogType,
        val message: String
    )

    enum class LogType { INFO, ANOMALY, API_SUCCESS, API_ERROR, GPS }

    val eventLog = mutableStateListOf<LogEntry>()

    fun log(type: LogType, message: String) {
        eventLog.add(0, LogEntry(type = type, message = message))
        // Keep only last 50 entries in RAM
        while (eventLog.size > 50) {
            eventLog.removeLastOrNull()
        }
    }

    fun reset() {
        totalAnomaliesDetected.value = 0
        totalApiCallsSent.value = 0
        totalApiErrors.value = 0
        bufferSize.value = 0
        currentJerk.value = 0f
        currentLat.value = 0.0
        currentLon.value = 0.0
        isScanning.value = false
        eventLog.clear()
    }
}
