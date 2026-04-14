package com.roadhealth.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.roadhealth.app.data.ScannerState
import com.roadhealth.app.service.OverlayService
import com.roadhealth.app.service.SensorService
import com.roadhealth.app.ui.theme.DigitalRoadHealthTheme
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : ComponentActivity() {

    private var permissionsGranted = mutableStateOf(false)
    private var overlayPermissionGranted = mutableStateOf(false)
    private var isServiceRunning = mutableStateOf(false)

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.values.all { it }
        permissionsGranted.value = allGranted
        if (!allGranted) {
            Toast.makeText(this, "Location permission is required for road scanning", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        checkPermissions()

        setContent {
            DigitalRoadHealthTheme {
                RoadHealthApp(
                    permissionsGranted = permissionsGranted.value,
                    overlayPermissionGranted = overlayPermissionGranted.value,
                    isServiceRunning = isServiceRunning.value,
                    onRequestPermissions = { requestPermissions() },
                    onRequestOverlay = { requestOverlayPermission() },
                    onToggleService = { toggleService() }
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        checkPermissions()
    }

    private fun checkPermissions() {
        permissionsGranted.value = ContextCompat.checkSelfPermission(
            this, Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        overlayPermissionGranted.value = Settings.canDrawOverlays(this)
    }

    private fun requestPermissions() {
        val perms = mutableListOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            perms.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        permissionLauncher.launch(perms.toTypedArray())
    }

    private fun requestOverlayPermission() {
        val intent = Intent(
            Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
            Uri.parse("package:$packageName")
        )
        startActivity(intent)
    }

    private fun toggleService() {
        if (isServiceRunning.value) {
            stopService(Intent(this, OverlayService::class.java))
            stopService(Intent(this, SensorService::class.java))
            isServiceRunning.value = false
        } else {
            ScannerState.reset()
            startService(Intent(this, OverlayService::class.java))
            isServiceRunning.value = true
        }
    }
}

// ─────────────────────────────────────────────────────────────
// Compose UI
// ─────────────────────────────────────────────────────────────

@Composable
fun RoadHealthApp(
    permissionsGranted: Boolean,
    overlayPermissionGranted: Boolean,
    isServiceRunning: Boolean,
    onRequestPermissions: () -> Unit,
    onRequestOverlay: () -> Unit,
    onToggleService: () -> Unit
) {
    val bgGradient = Brush.verticalGradient(
        colors = listOf(Color(0xFF0A0E1A), Color(0xFF101828), Color(0xFF162032))
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(bgGradient)
            .systemBarsPadding()
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 20.dp)
        ) {
            Spacer(modifier = Modifier.height(16.dp))

            // Header
            Text(
                text = "Digital Road Health",
                fontSize = 26.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color(0xFF00BFFF),
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth()
            )
            Text(
                text = "CROWDSOURCED ROAD SCANNER",
                fontSize = 10.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF6B7280),
                letterSpacing = 3.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(20.dp))

            // Permissions (only show if not granted)
            if (!permissionsGranted || !overlayPermissionGranted) {
                PermissionRow("Location Access", permissionsGranted, onRequestPermissions)
                Spacer(modifier = Modifier.height(8.dp))
                PermissionRow("Overlay Permission", overlayPermissionGranted, onRequestOverlay)
                Spacer(modifier = Modifier.height(16.dp))
            }

            // Live Stats Grid
            LiveStatsGrid()

            Spacer(modifier = Modifier.height(12.dp))

            // GPS Info Bar
            GpsBar()

            Spacer(modifier = Modifier.height(12.dp))

            // Event Log
            Text(
                text = "LIVE EVENT LOG",
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF6B7280),
                letterSpacing = 2.sp
            )
            Spacer(modifier = Modifier.height(8.dp))
            EventLogList(modifier = Modifier.weight(1f))

            Spacer(modifier = Modifier.height(12.dp))

            // Action Button
            val allReady = permissionsGranted && overlayPermissionGranted
            Button(
                onClick = { if (allReady) onToggleService() },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                enabled = allReady,
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isServiceRunning) Color(0xFFEF4444) else Color(0xFF00BFFF),
                    disabledContainerColor = Color(0xFF1F2937)
                )
            ) {
                Text(
                    text = if (isServiceRunning) "⏹  STOP SCANNING" else "▶  ACTIVATE OVERLAY",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Tap to activate the floating overlay button.\nOpen any navigation app and tap the button to start scanning.",
                fontSize = 11.sp,
                color = Color(0xFF4B5563),
                textAlign = TextAlign.Center,
                lineHeight = 16.sp,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}

// ─────────────────────────────────────────────────────────────
// Live Stats Grid
// ─────────────────────────────────────────────────────────────

@Composable
fun LiveStatsGrid() {
    val anomalies = ScannerState.totalAnomaliesDetected.value
    val apiSent = ScannerState.totalApiCallsSent.value
    val apiErrors = ScannerState.totalApiErrors.value
    val bufferSize = ScannerState.bufferSize.value
    val jerk = ScannerState.currentJerk.value

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        StatCard("Anomalies", "$anomalies", Color(0xFFEF4444), Modifier.weight(1f))
        StatCard("API Sent", "$apiSent", Color(0xFF22C55E), Modifier.weight(1f))
        StatCard("Errors", "$apiErrors", Color(0xFFEAB308), Modifier.weight(1f))
    }

    Spacer(modifier = Modifier.height(8.dp))

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        StatCard("Buffer", "$bufferSize pts", Color(0xFF00BFFF), Modifier.weight(1f))
        StatCard("Jerk", "%.1f".format(jerk), 
            if (jerk > SensorService.JERK_THRESHOLD) Color(0xFFEF4444) else Color(0xFF6B7280),
            Modifier.weight(1f)
        )
        StatCard("Threshold", "${SensorService.JERK_THRESHOLD}", Color(0xFF374151), Modifier.weight(1f))
    }
}

@Composable
fun StatCard(label: String, value: String, valueColor: Color, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(Color(0xFF1A1F2E))
            .border(1.dp, Color(0xFF374151).copy(alpha = 0.3f), RoundedCornerShape(12.dp))
            .padding(horizontal = 12.dp, vertical = 10.dp)
    ) {
        Column {
            Text(
                text = label,
                fontSize = 9.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF6B7280),
                letterSpacing = 1.sp
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = value,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = valueColor
            )
        }
    }
}

// ─────────────────────────────────────────────────────────────
// GPS Bar
// ─────────────────────────────────────────────────────────────

@Composable
fun GpsBar() {
    val lat = ScannerState.currentLat.value
    val lon = ScannerState.currentLon.value
    val hasGps = lat != 0.0 || lon != 0.0

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(Color(0xFF1A1F2E))
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(if (hasGps) Color(0xFF22C55E) else Color(0xFFEF4444))
        )
        Spacer(modifier = Modifier.width(10.dp))
        Text(
            text = if (hasGps) "GPS: %.5f, %.5f".format(lat, lon) else "GPS: Waiting for fix...",
            fontSize = 11.sp,
            fontWeight = FontWeight.Medium,
            color = if (hasGps) Color(0xFF9CA3AF) else Color(0xFF6B7280),
            letterSpacing = 0.5.sp
        )
    }
}

// ─────────────────────────────────────────────────────────────
// Event Log
// ─────────────────────────────────────────────────────────────

@Composable
fun EventLogList(modifier: Modifier = Modifier) {
    val events = ScannerState.eventLog
    val timeFormatter = remember { SimpleDateFormat("HH:mm:ss", Locale.getDefault()) }

    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(Color(0xFF111827))
            .border(1.dp, Color(0xFF1F2937), RoundedCornerShape(14.dp))
    ) {
        if (events.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "No events yet.\nActivate the scanner to see live data.",
                    fontSize = 12.sp,
                    color = Color(0xFF374151),
                    textAlign = TextAlign.Center,
                    lineHeight = 18.sp
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier.padding(8.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                items(events) { entry ->
                    EventLogRow(entry, timeFormatter)
                }
            }
        }
    }
}

@Composable
fun EventLogRow(entry: ScannerState.LogEntry, timeFormatter: SimpleDateFormat) {
    val dotColor = when (entry.type) {
        ScannerState.LogType.INFO -> Color(0xFF6B7280)
        ScannerState.LogType.ANOMALY -> Color(0xFFEF4444)
        ScannerState.LogType.API_SUCCESS -> Color(0xFF22C55E)
        ScannerState.LogType.API_ERROR -> Color(0xFFEAB308)
        ScannerState.LogType.GPS -> Color(0xFF00BFFF)
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(Color(0xFF1A1F2E).copy(alpha = 0.5f))
            .padding(horizontal = 10.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(6.dp)
                .clip(CircleShape)
                .background(dotColor)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = timeFormatter.format(Date(entry.timestamp)),
            fontSize = 9.sp,
            fontWeight = FontWeight.Medium,
            color = Color(0xFF4B5563)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = entry.message,
            fontSize = 11.sp,
            color = Color(0xFF9CA3AF),
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f)
        )
    }
}

// ─────────────────────────────────────────────────────────────
// Permission Row
// ─────────────────────────────────────────────────────────────

@Composable
fun PermissionRow(label: String, granted: Boolean, onRequest: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(Color(0xFF1A1F2E))
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(if (granted) Color(0xFF22C55E) else Color(0xFFEF4444))
            )
            Spacer(modifier = Modifier.width(12.dp))
            Text(
                text = label,
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
                color = Color.White
            )
        }
        if (!granted) {
            TextButton(onClick = onRequest) {
                Text(
                    text = "GRANT",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF00BFFF),
                    letterSpacing = 1.sp
                )
            }
        } else {
            Text("✓", fontSize = 14.sp, color = Color(0xFF22C55E), fontWeight = FontWeight.Bold)
        }
    }
}