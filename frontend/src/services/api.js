import axios from 'axios';

// ──────────────────────────────────────────────
// Supabase Configuration (Cloud PostgreSQL)
// ──────────────────────────────────────────────
const SUPABASE_URL = 'https://spbmkcmcdtqebammaarf.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNwYm1rY21jZHRxZWJhbW1hYXJmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2ODI5MTcsImV4cCI6MjA4ODI1ODkxN30.NlwkAx0Nkyu_tG8mCgSUgRx5qc5zCTXQZyrm0TKNb9k';

// Supabase REST API client
const supabase = axios.create({
    baseURL: `${SUPABASE_URL}/rest/v1`,
    headers: {
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
});

// ──────────────────────────────────────────────
// Local FastAPI fallback (for development)
// ──────────────────────────────────────────────
const LOCAL_API_URL = 'https://digital-road-health-api.onrender.com/api';

// Toggle: set to true to use cloud Supabase, false for local dev
const USE_CLOUD = true;

/**
 * Fetch verified potholes from the database.
 * Cloud mode: reads directly from Supabase PostgreSQL (report_count >= 2, last 12 hours)
 * Local mode: reads from FastAPI backend
 */
export const fetchPotholes = async () => {
    try {
        if (USE_CLOUD) {
            const twelveHoursAgo = new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString();
            
            const response = await supabase.get('/potholes', {
                params: {
                    'report_count': 'gte.2',
                    'last_reported': `gte.${twelveHoursAgo}`,
                    'order': 'last_reported.desc',
                    'limit': 1000
                }
            });
            return response.data;
        } else {
            const response = await axios.get(`${LOCAL_API_URL}/potholes`);
            return response.data;
        }
    } catch (error) {
        console.error("Error fetching potholes:", error);
        return [];
    }
};

/**
 * Insert or cluster an anomaly into Supabase.
 * Called by the prediction edge function or directly.
 */
export const reportAnomaly = async (anomalyData) => {
    try {
        const response = await supabase.post('/potholes', anomalyData);
        return response.data;
    } catch (error) {
        console.error("Error reporting anomaly:", error);
        return null;
    }
};
