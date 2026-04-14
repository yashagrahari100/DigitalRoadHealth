package com.roadhealth.app.service

import android.annotation.SuppressLint
import android.app.*
import android.content.Intent
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.google.android.gms.location.*
import com.roadhealth.app.MainActivity
import com.roadhealth.app.R
import com.roadhealth.app.data.ScannerState
import com.roadhealth.app.network.ApiClient
import com.roadhealth.app.network.SensorPayload
import com.roadhealth.app.network.SupabasePotholeInsert
import kotlinx.coroutines.*
import kotlin.math.sqrt

/**
 * Foreground Service that collects high-frequency sensor data (accelerometer + gyroscope),
 * maintains a rolling 3-second RAM buffer, and fires anomaly snapshots to the backend
 * when a significant jerk is detected.
 *
 * Privacy: No data is written to disk. Only isolated 3-second windows + a single GPS
 * coordinate are transmitted when an anomaly threshold is exceeded.
 */
class SensorService : Service(), SensorEventListener {

    companion object {
        const val TAG = "SensorService"
        const val CHANNEL_ID = "road_health_channel"
        const val NOTIFICATION_ID = 1
        const val BUFFER_DURATION_MS = 3000L   // 3-second rolling window
        const val JERK_THRESHOLD = 18.0f       // Anomaly trigger threshold (m/s³)
        const val COOLDOWN_MS = 5000L          // Min gap between reports to avoid spam
    }

    private lateinit var sensorManager: SensorManager
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    // Rolling RAM buffer - never touches disk
    private data class SensorSnapshot(
        val timestamp: Long,
        val accX: Float, val accY: Float, val accZ: Float,
        val gyroX: Float, val gyroY: Float, val gyroZ: Float
    )

    private val buffer = mutableListOf<SensorSnapshot>()
    private var lastAccX = 0f; private var lastAccY = 0f; private var lastAccZ = 0f
    private var lastGyroX = 0f; private var lastGyroY = 0f; private var lastGyroZ = 0f
    private var lastReportTime = 0L
    private var currentLat = 0.0
    private var currentLon = 0.0
    private var currentSpeed = 0f

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        sensorManager = getSystemService(SENSOR_SERVICE) as SensorManager
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = buildNotification("Scanning road surface...")
        startForeground(NOTIFICATION_ID, notification)
        startSensorListeners()
        startLocationUpdates()

        ScannerState.isScanning.value = true
        ScannerState.log(ScannerState.LogType.INFO, "Sensor service started — listening at max Hz")

        Log.i(TAG, "Road scanning started")
        return START_STICKY
    }

    override fun onDestroy() {
        sensorManager.unregisterListener(this)
        serviceScope.cancel()

        ScannerState.isScanning.value = false
        ScannerState.log(ScannerState.LogType.INFO, "Sensor service stopped")

        Log.i(TAG, "Road scanning stopped")
        super.onDestroy()
    }

    // ─────────────────────────────────────────────────────────────
    // Sensor Listeners
    // ─────────────────────────────────────────────────────────────

    private fun startSensorListeners() {
        sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)?.let { accel ->
            sensorManager.registerListener(this, accel, SensorManager.SENSOR_DELAY_FASTEST)
            ScannerState.log(ScannerState.LogType.INFO, "Accelerometer registered")
        } ?: ScannerState.log(ScannerState.LogType.API_ERROR, "No accelerometer found!")

        sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)?.let { gyro ->
            sensorManager.registerListener(this, gyro, SensorManager.SENSOR_DELAY_FASTEST)
            ScannerState.log(ScannerState.LogType.INFO, "Gyroscope registered")
        } ?: ScannerState.log(ScannerState.LogType.API_ERROR, "No gyroscope found!")
    }

    @SuppressLint("MissingPermission")
    private fun startLocationUpdates() {
        val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 2000)
            .setMinUpdateIntervalMillis(1000)
            .build()

        fusedLocationClient.requestLocationUpdates(request, object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                result.lastLocation?.let { loc ->
                    currentLat = loc.latitude
                    currentLon = loc.longitude
                    currentSpeed = loc.speed
                    ScannerState.currentLat.value = loc.latitude
                    ScannerState.currentLon.value = loc.longitude
                }
            }
        }, mainLooper)

        ScannerState.log(ScannerState.LogType.GPS, "GPS listener started — waiting for fix...")
    }

    override fun onSensorChanged(event: SensorEvent) {
        when (event.sensor.type) {
            Sensor.TYPE_ACCELEROMETER -> {
                lastAccX = event.values[0]
                lastAccY = event.values[1]
                lastAccZ = event.values[2]
            }
            Sensor.TYPE_GYROSCOPE -> {
                lastGyroX = event.values[0]
                lastGyroY = event.values[1]
                lastGyroZ = event.values[2]
            }
        }

        val now = System.currentTimeMillis()
        val snapshot = SensorSnapshot(now, lastAccX, lastAccY, lastAccZ, lastGyroX, lastGyroY, lastGyroZ)

        synchronized(buffer) {
            buffer.add(snapshot)
            buffer.removeAll { it.timestamp < now - BUFFER_DURATION_MS }
            ScannerState.bufferSize.value = buffer.size
        }

        checkForAnomaly(now)
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    // ─────────────────────────────────────────────────────────────
    // Edge Computing: On-device anomaly detection
    // ─────────────────────────────────────────────────────────────

    private fun checkForAnomaly(now: Long) {
        if (now - lastReportTime < COOLDOWN_MS) return
        if (currentLat == 0.0 && currentLon == 0.0) return

        val bufferCopy: List<SensorSnapshot>
        synchronized(buffer) {
            if (buffer.size < 20) return
            bufferCopy = buffer.toList()
        }

        val accMagnitudes = bufferCopy.map { sqrt(it.accX * it.accX + it.accY * it.accY + it.accZ * it.accZ) }
        val jerk = accMagnitudes.max() - accMagnitudes.min()

        // Update live jerk reading for UI
        ScannerState.currentJerk.value = jerk

        if (jerk > JERK_THRESHOLD) {
            lastReportTime = now
            ScannerState.totalAnomaliesDetected.value++
            ScannerState.log(
                ScannerState.LogType.ANOMALY,
                "Anomaly detected! Jerk=%.1f at (%.4f, %.4f)".format(jerk, currentLat, currentLon)
            )
            fireAnomalyReport(bufferCopy)
        }
    }

    private fun fireAnomalyReport(data: List<SensorSnapshot>) {
        val accMags = data.map { sqrt(it.accX * it.accX + it.accY * it.accY + it.accZ * it.accZ) }
        val gyroMags = data.map { sqrt(it.gyroX * it.gyroX + it.gyroY * it.gyroY + it.gyroZ * it.gyroZ) }

        val accMean = accMags.average().toFloat()
        val accStd = stdDev(accMags)
        val gyroMean = gyroMags.average().toFloat()
        val gyroStd = stdDev(gyroMags)
        val accMag = accMags.max()
        val gyroMag = gyroMags.max()
        val jerk = accMags.max() - accMags.min()

        serviceScope.launch {
            try {
                if (ApiClient.USE_CLOUD) {
                    // ── Cloud Mode: On-device classification + direct Supabase insert ──
                    // Simple rule-based severity classification on-device
                    val severity = when {
                        jerk > 30f -> "High"
                        jerk > 22f -> "Medium"
                        else -> "Low"
                    }
                    val anomalyType = if (gyroMag > 3.0f) "speed_breaker" else "pothole"

                    val insert = SupabasePotholeInsert(
                        latitude = currentLat,
                        longitude = currentLon,
                        anomaly_type = anomalyType,
                        severity = severity
                    )

                    ApiClient.supabaseApi.insertPothole(
                        apiKey = ApiClient.SUPABASE_ANON_KEY,
                        auth = "Bearer ${ApiClient.SUPABASE_ANON_KEY}",
                        pothole = insert
                    )

                    ScannerState.totalApiCallsSent.value++
                    ScannerState.log(
                        ScannerState.LogType.API_SUCCESS,
                        "→ Cloud: $anomalyType ($severity) at %.4f, %.4f".format(currentLat, currentLon)
                    )
                } else {
                    // ── Local Mode: Send to FastAPI for ML prediction ──
                    val apiReadings = data.map {
                        com.roadhealth.app.network.SensorReading(
                            timestamp = it.timestamp,
                            accX = it.accX, accY = it.accY, accZ = it.accZ,
                            gyroX = it.gyroX, gyroY = it.gyroY, gyroZ = it.gyroZ
                        )
                    }
                    val payload = SensorPayload(
                        speed = currentSpeed,
                        latitude = currentLat,
                        longitude = currentLon,
                        readings = apiReadings
                    )
                    val response = ApiClient.api.sendSensorData(payload)
                    ScannerState.totalApiCallsSent.value++
                    ScannerState.log(
                        ScannerState.LogType.API_SUCCESS,
                        "→ Server: ${response.message}"
                    )
                }

                val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                nm.notify(NOTIFICATION_ID, buildNotification(
                    "Scanning... ${ScannerState.totalAnomaliesDetected.value} anomalies | ${ScannerState.totalApiCallsSent.value} sent"
                ))
            } catch (e: Exception) {
                ScannerState.totalApiErrors.value++
                ScannerState.log(
                    ScannerState.LogType.API_ERROR,
                    "✗ Failed: ${e.message?.take(80)}"
                )
                Log.e(TAG, "Failed to send report: ${e.message}")
            }
        }
    }

    private fun stdDev(values: List<Float>): Float {
        val mean = values.average()
        val variance = values.map { (it - mean) * (it - mean) }.average()
        return sqrt(variance).toFloat()
    }

    // ─────────────────────────────────────────────────────────────
    // Notification
    // ─────────────────────────────────────────────────────────────

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Road Health Scanner",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Shows when road scanning is active"
        }
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(channel)
    }

    private fun buildNotification(text: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Digital Road Health")
            .setContentText(text)
            .setSmallIcon(R.drawable.ic_road_scan)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }
}
