package com.roadhealth.app.service

import android.app.Service
import android.content.Intent
import android.graphics.PixelFormat
import android.os.IBinder
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.util.TypedValue
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.os.Build

/**
 * Floating Overlay Service - Draws a translucent "Start Scanning" button
 * on top of other apps (like Google Maps). When tapped, it starts the
 * SensorService foreground service to begin road scanning.
 *
 * This provides explicit user consent — the user must physically tap
 * the overlay button to begin contributing road data.
 */
class OverlayService : Service() {

    private var windowManager: WindowManager? = null
    private var overlayView: View? = null
    private var isScanning = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        showOverlay()
    }

    override fun onDestroy() {
        overlayView?.let { windowManager?.removeView(it) }
        super.onDestroy()
    }

    private fun showOverlay() {
        // Create the floating button programmatically (no XML needed)
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(16), dp(12), dp(20), dp(12))

            // Glassmorphic background
            background = GradientDrawable().apply {
                shape = GradientDrawable.RECTANGLE
                cornerRadius = dp(28).toFloat()
                setColor(Color.parseColor("#E6101820"))
                setStroke(dp(1), Color.parseColor("#3300BFFF"))
            }
            elevation = dp(8).toFloat()
        }

        // Pulsing dot indicator
        val dot = View(this).apply {
            val dotBg = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(Color.parseColor("#22C55E"))
            }
            background = dotBg
            layoutParams = LinearLayout.LayoutParams(dp(10), dp(10)).apply {
                setMargins(0, 0, dp(10), 0)
            }
        }

        // Label text
        val label = TextView(this).apply {
            text = "Start Road Scan"
            setTextColor(Color.WHITE)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f)
            typeface = android.graphics.Typeface.create("sans-serif-medium", android.graphics.Typeface.NORMAL)
            letterSpacing = 0.05f
        }

        container.addView(dot)
        container.addView(label)

        // Layout params for overlay window
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
            y = dp(120) // Bottom margin
        }

        // Make it draggable
        var initialX = 0
        var initialY = 0
        var initialTouchX = 0f
        var initialTouchY = 0f

        container.setOnTouchListener { v, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    initialX = params.x
                    initialY = params.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    params.x = initialX + (event.rawX - initialTouchX).toInt()
                    params.y = initialY - (event.rawY - initialTouchY).toInt()
                    windowManager?.updateViewLayout(container, params)
                    true
                }
                MotionEvent.ACTION_UP -> {
                    val dx = Math.abs(event.rawX - initialTouchX)
                    val dy = Math.abs(event.rawY - initialTouchY)
                    if (dx < 10 && dy < 10) {
                        // It was a tap, not a drag
                        toggleScanning(label, dot)
                    }
                    true
                }
                else -> false
            }
        }

        overlayView = container
        windowManager?.addView(container, params)
    }

    private fun toggleScanning(label: TextView, dot: View) {
        isScanning = !isScanning
        val serviceIntent = Intent(this, SensorService::class.java)

        if (isScanning) {
            label.text = "⏹ Stop Scanning"
            (dot.background as? GradientDrawable)?.setColor(Color.parseColor("#EF4444"))
            startForegroundService(serviceIntent)
        } else {
            label.text = "Start Road Scan"
            (dot.background as? GradientDrawable)?.setColor(Color.parseColor("#22C55E"))
            stopService(serviceIntent)
        }
    }

    private fun dp(value: Int): Int {
        return TypedValue.applyDimension(
            TypedValue.COMPLEX_UNIT_DIP,
            value.toFloat(),
            resources.displayMetrics
        ).toInt()
    }
}
