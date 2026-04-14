import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { fetchPotholes } from '../services/api';
import L from 'leaflet';
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

const MapDashboard = () => {
    const [anomalies, setAnomalies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [center, setCenter] = useState([28.7041, 77.1025]);
    const [theme, setTheme] = useState('dark');
    const markerRefs = React.useRef({});
    
    // Filters
    const [showPotholes, setShowPotholes] = useState(true);
    const [showSpeedBreakers, setShowSpeedBreakers] = useState(true);

    const loadData = async () => {
        setLoading(true);
        const data = await fetchPotholes();
        setAnomalies(data);
        if (data && data.length > 0) {
            const latest = data[data.length - 1];
            setCenter([latest.latitude, latest.longitude]);
        }
        setLoading(false);
    };

    useEffect(() => {
        loadData();
        const interval = setInterval(loadData, 10000); 
        return () => clearInterval(interval);
    }, []);

    const toggleTheme = () => {
        setTheme(prev => prev === 'dark' ? 'light' : 'dark');
    };

    const exportToCSV = () => {
        const rows = [
            ["ID", "Type", "Severity", "Latitude", "Longitude", "Timestamp"]
        ];
        
        filteredAnomalies.forEach(a => {
            rows.push([
                a.id, 
                a.anomaly_type || 'pothole', 
                a.severity || 'N/A', 
                a.latitude, 
                a.longitude, 
                new Date(a.timestamp).toISOString()
            ]);
        });

        const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\n");
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `road_health_report_${new Date().getTime()}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const getMarkerIcon = (anomaly) => {
        const type = anomaly.anomaly_type || 'pothole';
        let bgColor = 'bg-anomaly-pothole';
        let glowColor = 'bg-anomaly-pothole/40';

        if (type === 'speed_breaker') {
            bgColor = 'bg-anomaly-speed_breaker';
            glowColor = 'bg-anomaly-speed_breaker/40';
        } else {
            if (anomaly.severity === 'Medium') {
                bgColor = 'bg-yellow-500';
                glowColor = 'bg-yellow-500/40';
            } else if (anomaly.severity === 'Low') {
                bgColor = 'bg-green-500';
                glowColor = 'bg-green-500/40';
            }
        }

        return L.divIcon({
            html: `<div class="relative flex items-center justify-center w-4 h-4 group">
                     <div class="relative w-3 h-3 border-2 border-dark-900 rounded-full ${bgColor} shadow-md z-10 transition-transform duration-300 group-hover:scale-150"></div>
                   </div>`,
            className: 'custom-anomaly-marker',
            iconSize: [16, 16],
            iconAnchor: [8, 8],
            popupAnchor: [0, -12]
        });
    };

    const filteredAnomalies = anomalies.filter(p => {
        const isPothole = (!p.anomaly_type || p.anomaly_type === 'pothole');
        if (isPothole && !showPotholes) return false;
        if (!isPothole && !showSpeedBreakers) return false;
        return true;
    });

    const potholesCount = anomalies.filter(p => !p.anomaly_type || p.anomaly_type === 'pothole').length;
    const speedBreakersCount = anomalies.filter(p => p.anomaly_type === 'speed_breaker').length;
    const highSeverityCount = anomalies.filter(p => (!p.anomaly_type || p.anomaly_type === 'pothole') && p.severity === 'High').length;

    // Theme Classes
    const isDark = theme === 'dark';
    const bgBase = isDark ? 'bg-dark-900' : 'bg-gray-100';
    const textBase = isDark ? 'text-white' : 'text-gray-900';
    const textMuted = isDark ? 'text-gray-400' : 'text-gray-500';
    
    // Glass styles
    const glassPanel = isDark 
        ? 'bg-glass backdrop-blur-md border border-dark-600/50 shadow-2xl'
        : 'bg-white/80 backdrop-blur-md border border-gray-200 shadow-xl';

    return (
        <div className={`relative h-[100dvh] w-screen overflow-hidden font-sans ${bgBase} ${textBase}`}>
            
            {/* Map Background */}
            <div className="absolute inset-0 z-0">
                <MapContainer
                    center={center}
                    zoom={14}
                    style={{ height: '100%', width: '100%' }}
                    className="z-0"
                    key={center.join(',') + theme}
                >
                    <TileLayer
                        attribution='&copy; CARTO'
                        url={isDark ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"}
                    />
                    {filteredAnomalies.map((anomaly) => (
                        <Marker
                            key={anomaly.id}
                            position={[anomaly.latitude, anomaly.longitude]}
                            icon={getMarkerIcon(anomaly)}
                            ref={(r) => { if (r) markerRefs.current[anomaly.id] = r; }}
                        >
                            <Popup className={`custom-popup ${isDark ? 'dark-popup' : 'light-popup'}`}>
                                <div className="text-center p-2 min-w-[150px]">
                                    <strong className="block text-lg mb-1 capitalize text-accent-500">
                                        {(anomaly.anomaly_type || 'pothole').replace('_', ' ')}
                                        <span className="text-xs ml-2 opacity-50">#{anomaly.id}</span>
                                    </strong>
                                    <div className={`text-sm mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                                        Severity: <span className="font-bold">{anomaly.severity || 'N/A'}</span>
                                    </div>
                                    <div className={`text-[10px] mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                                        {new Date(anomaly.timestamp).toLocaleTimeString()}
                                    </div>
                                    <div className={`mt-2 border-t ${isDark ? 'border-dark-600/50' : 'border-gray-200'} pt-2 text-center`}>
                                        <a 
                                            href={`https://www.google.com/maps?q=${anomaly.latitude},${anomaly.longitude}`} 
                                            target="_blank" 
                                            rel="noreferrer"
                                            className={`inline-flex items-center justify-center space-x-1 text-[10px] uppercase font-bold tracking-wider ${isDark ? 'text-accent-400 hover:text-accent-300' : 'text-accent-600 hover:text-accent-500'} transition-colors cursor-pointer w-full py-1 rounded hover:bg-dark-600/20`}
                                        >
                                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                                            <span>Share Location</span>
                                        </a>
                                    </div>
                                </div>
                            </Popup>
                        </Marker>
                    ))}
                </MapContainer>
            </div>

            {/* Prototype Badge */}
            <div className="absolute top-2 w-full z-20 pointer-events-none flex justify-center">
                <div className={`${isDark ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' : 'bg-yellow-100 text-yellow-800 border-yellow-300'} text-[10px] px-4 py-1 rounded-full border shadow-sm font-bold uppercase tracking-wider backdrop-blur-sm`}>
                    Prototype: Data Collected on Two-Wheeler
                </div>
            </div>

            {/* Top Header Overlay */}
            <div className="absolute top-8 w-full z-10 pointer-events-none px-6 flex justify-between items-start">
                <div className={`${glassPanel} rounded-2xl p-4 sm:p-5 pointer-events-auto transition-colors`}>
                    <h1 className="text-2xl sm:text-3xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-accent-500 to-cyan-500">
                        Digital Road Health
                    </h1>
                    <p className={`text-xs sm:text-sm mt-1 uppercase tracking-wider font-semibold ${textMuted}`}>City Infrastructure Monitoring</p>
                </div>
                
                <div className="flex flex-col space-y-3 pointer-events-auto items-end">
                    <div className={`${glassPanel} rounded-full px-4 sm:px-5 py-2 flex items-center space-x-3`}>
                        <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.8)]"></div>
                        <span className={`text-xs sm:text-sm font-semibold uppercase tracking-widest ${isDark ? 'text-gray-200' : 'text-gray-700'}`}>Live Sensor Feed</span>
                    </div>

                    <button 
                        onClick={toggleTheme}
                        className={`${glassPanel} rounded-full px-4 py-2 text-xs font-bold uppercase tracking-wider flex items-center space-x-2 hover:opacity-80`}
                    >
                        <span>{isDark ? '☀️ Light Mode' : '🌙 Dark Mode'}</span>
                    </button>
                    
                    <button 
                        onClick={exportToCSV}
                        className="bg-accent-600 hover:bg-accent-500 text-white rounded-full px-4 py-2 text-xs font-bold uppercase tracking-wider shadow-lg transition-colors cursor-pointer"
                    >
                        📥 Export CSV
                    </button>
                </div>
            </div>

            {/* Bottom Stats & List Overlay */}
            <div className="absolute bottom-0 w-full z-10 pointer-events-none p-6">
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 pointer-events-none">
                    
                    {/* Stats Box (col-span-3) */}
                    <div className="lg:col-span-3 flex flex-col justify-end items-start space-y-3">
                        
                        {/* Filters Bar */}
                        <div className="flex space-x-2 pointer-events-none">
                            <button 
                                onClick={() => setShowPotholes(!showPotholes)}
                                className={`px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider border pointer-events-auto transition-all cursor-pointer ${
                                    showPotholes 
                                    ? 'bg-anomaly-pothole/20 text-anomaly-pothole border-anomaly-pothole' 
                                    : 'bg-dark-800/10 text-gray-500 border-gray-500/30'
                                }`}
                            >
                                {showPotholes ? '✓ Potholes' : 'Hidden Potholes'}
                            </button>
                            <button 
                                onClick={() => setShowSpeedBreakers(!showSpeedBreakers)}
                                className={`px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider border pointer-events-auto transition-all cursor-pointer ${
                                    showSpeedBreakers 
                                    ? 'bg-anomaly-speed_breaker/20 text-anomaly-speed_breaker border-anomaly-speed_breaker' 
                                    : 'bg-dark-800/10 text-gray-500 border-gray-500/30'
                                }`}
                            >
                                {showSpeedBreakers ? '✓ Speed Breakers' : 'Hidden Speed Breakers'}
                            </button>
                        </div>

                        <div className={`${glassPanel} rounded-xl px-5 py-3 flex gap-6 sm:gap-8 pointer-events-auto transition-colors w-max`}>
                            <div>
                                <p className={`text-[10px] uppercase tracking-widest mb-0.5 ${textMuted}`}>Total Potholes</p>
                                <p className="text-2xl font-bold text-anomaly-pothole leading-none">{potholesCount}</p>
                            </div>
                            <div className={`w-px ${isDark ? 'bg-dark-600/50' : 'bg-gray-300'}`}></div>
                            <div>
                                <p className={`text-[10px] uppercase tracking-widest mb-0.5 ${textMuted}`}>Speed Breakers</p>
                                <p className="text-2xl font-bold text-anomaly-speed_breaker leading-none">{speedBreakersCount}</p>
                            </div>
                            <div className={`w-px ${isDark ? 'bg-dark-600/50' : 'bg-gray-300'}`}></div>
                            <div>
                                <p className={`text-[10px] uppercase tracking-widest mb-0.5 ${textMuted}`}>High Sev.</p>
                                <p className="text-2xl font-bold text-yellow-500 leading-none">{highSeverityCount}</p>
                            </div>
                        </div>
                    </div>

                    {/* Sidebar / List View */}
                    <div className={`${glassPanel} rounded-2xl flex flex-col h-72 pointer-events-auto transition-colors`}>
                        <div className={`p-4 border-b ${isDark ? 'border-dark-600/50' : 'border-gray-200'} flex justify-between items-center`}>
                            <h2 className="font-semibold text-sm uppercase tracking-wider">Recent Activity</h2>
                            <button onClick={loadData} className="text-accent-500 hover:opacity-80 transition-opacity cursor-pointer">
                                <svg className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                            </button>
                        </div>
                        <div className="flex-grow overflow-y-auto p-3 space-y-2 custom-scrollbar">
                            {loading && filteredAnomalies.length === 0 ? (
                                <div className="flex justify-center items-center h-full text-accent-500">Loading...</div>
                            ) : filteredAnomalies.length === 0 ? (
                                <div className={`text-center text-sm py-4 ${textMuted}`}>No data visible.</div>
                            ) : (
                                filteredAnomalies.slice().reverse().map((p) => (
                                    <div key={p.id} className={`${isDark ? 'bg-dark-800/60 border-dark-600/30 hover:border-accent-400/50' : 'bg-white border-gray-200 hover:border-accent-500'} p-3 rounded-xl border transition-colors flex items-center justify-between group cursor-pointer`} onClick={() => {
                                        setCenter([p.latitude, p.longitude]);
                                        setTimeout(() => {
                                            const marker = markerRefs.current[p.id];
                                            if (marker) marker.openPopup();
                                        }, 150);
                                    }}>
                                        <div>
                                            <div className="flex items-center space-x-2">
                                                <span className={`text-xs font-bold uppercase tracking-wider ${(p.anomaly_type||'pothole') === 'speed_breaker' ? 'text-anomaly-speed_breaker' : 'text-anomaly-pothole'}`}>
                                                    {(p.anomaly_type||'pothole').replace('_', ' ')}
                                                </span>
                                                <span className={`text-[9px] px-1.5 py-0.5 rounded ${isDark ? 'bg-dark-700 text-gray-400' : 'bg-gray-100 text-gray-500'}`}>#{p.id}</span>
                                            </div>
                                            <p className={`text-[10px] mt-1 ${textMuted}`}>{new Date(p.timestamp).toLocaleTimeString()}</p>
                                        </div>
                                        {p.anomaly_type !== 'speed_breaker' && (
                                            <span className={`text-[10px] px-2 py-1 rounded-md ${isDark ? 'bg-dark-700/50 text-gray-300' : 'bg-gray-50 text-gray-700'}`}>
                                                Sev: {p.severity}
                                            </span>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MapDashboard;
