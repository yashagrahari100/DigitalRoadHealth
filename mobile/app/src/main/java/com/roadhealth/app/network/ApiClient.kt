package com.roadhealth.app.network

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor

/**
 * Data class matching the FastAPI SensorDataInput schema.
 * Used when posting to the local FastAPI prediction endpoint.
 */
data class SensorReading(
    val timestamp: Long,
    val accX: Float,
    val accY: Float,
    val accZ: Float,
    val gyroX: Float,
    val gyroY: Float,
    val gyroZ: Float
)

data class SensorPayload(
    val speed: Float,
    val latitude: Double,
    val longitude: Double,
    val readings: List<SensorReading>
)

data class PredictionResponse(
    val is_anomaly: Boolean,
    val anomaly_type: String?,
    val severity: String?,
    val message: String
)

/**
 * Data class for inserting directly into Supabase potholes table.
 */
data class SupabasePotholeInsert(
    val latitude: Double,
    val longitude: Double,
    val anomaly_type: String,
    val severity: String,
    val report_count: Int = 1
)

// ─────────────────────────────────────────────────────────────
// Local FastAPI API (for local dev with ML model)
// ─────────────────────────────────────────────────────────────

interface RoadHealthApi {
    @POST("/api/predict")
    suspend fun sendSensorData(@Body payload: SensorPayload): PredictionResponse
}

// ─────────────────────────────────────────────────────────────
// Supabase REST API (for cloud production)
// ─────────────────────────────────────────────────────────────

interface SupabaseApi {
    @POST("/rest/v1/potholes")
    suspend fun insertPothole(
        @Header("apikey") apiKey: String,
        @Header("Authorization") auth: String,
        @Header("Content-Type") contentType: String = "application/json",
        @Header("Prefer") prefer: String = "return=representation",
        @Body pothole: SupabasePotholeInsert
    ): List<Map<String, Any>>
}

/**
 * Singleton API client with both local and cloud modes.
 */
object ApiClient {

    // ── Configuration ──
    // Toggle this to switch between local dev and cloud production
    const val USE_CLOUD = false

    // Deployed FastAPI Python Server (Render Cloud)
    private const val LOCAL_BASE_URL = "https://digital-road-health-api.onrender.com"

    // Supabase Cloud
    const val SUPABASE_URL = "https://spbmkcmcdtqebammaarf.supabase.co"
    const val SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNwYm1rY21jZHRxZWJhbW1hYXJmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2ODI5MTcsImV4cCI6MjA4ODI1ODkxN30.NlwkAx0Nkyu_tG8mCgSUgRx5qc5zCTXQZyrm0TKNb9k"

    private val client = OkHttpClient.Builder()
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        })
        .build()

    // Local FastAPI client
    private val localRetrofit = Retrofit.Builder()
        .baseUrl(LOCAL_BASE_URL)
        .client(client)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val api: RoadHealthApi = localRetrofit.create(RoadHealthApi::class.java)

    // Supabase cloud client
    private val supabaseRetrofit = Retrofit.Builder()
        .baseUrl(SUPABASE_URL)
        .client(client)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val supabaseApi: SupabaseApi = supabaseRetrofit.create(SupabaseApi::class.java)
}
