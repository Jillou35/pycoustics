
import { useState, useEffect, useRef, useCallback } from 'react';
import { useAudioStream } from './hooks/useAudioStream';
import { VuMeter } from './components/VuMeter';
import { SpectrumAnalyzer } from './components/SpectrumAnalyzer';
import { PanningViewer } from './components/PanningViewer';
import { Mic, Square, Save, Sliders, Play, Download, Trash2 } from 'lucide-react';

// Types
interface Recording {
    id: number;
    filename: string;
    duration_seconds: number;
    timestamp: string;
}

function App() {
    const { isConnected, isRecording, rms, spectrum, panning, startAudio, startRecording, stopRecording, setSettings, lastRecording, sessionId } = useAudioStream();

    // UI State
    const [gain, setGain] = useState(0.0);
    const [cutoff, setCutoff] = useState(1000);
    const [filterEnabled, setFilterEnabled] = useState(false);
    const [integrationTime, setIntegrationTime] = useState(0.5);
    const [recordings, setRecordings] = useState<Recording[]>([]);
    const [started, setStarted] = useState(false);
    const [playingFile, setPlayingFile] = useState<string | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const apiUrl = import.meta.env.VITE_API_URL || `http://localhost:8000`;

    // Fetch recordings
    const fetchRecordings = useCallback(async () => {
        try {
            const response = await fetch(`${apiUrl}/recordings?session_id=${sessionId}`);
            if (response.ok) {
                const data = await response.json();
                setRecordings(data);
            } else {
                console.error("Failed to fetch recordings:", response.status, response.statusText);
            }
        } catch (error) {
            console.error("Error fetching recordings:", error);
        }
    }, [sessionId]);

    const deleteRecording = async (e: React.MouseEvent, filename: string) => {
        e.stopPropagation(); // Prevent playing
        if (!confirm(`Delete ${filename}?`)) return;

        try {
            const response = await fetch(`${apiUrl}/recordings/${filename}`, { method: 'DELETE' });
            if (response.ok) {
                fetchRecordings();
            } else {
                console.error("Failed to delete recording:", response.status, response.statusText);
            }
        } catch (error) {
            console.error("Failed to delete", error);
        }
    }

    useEffect(() => {
        fetchRecordings();
    }, [lastRecording]);

    useEffect(() => {
        setSettings(gain, filterEnabled, cutoff, integrationTime);
    }, [gain, cutoff, filterEnabled, integrationTime, isConnected]);

    const handleStart = async () => {
        await startAudio();
        setStarted(true);
    };

    const playRecording = (filename: string) => {
        if (audioRef.current) {
            audioRef.current.src = `${apiUrl}/recordings/${filename}`;
            audioRef.current.play();
            setPlayingFile(filename);
        }
    }

    return (
        <div className="container">
            <header style={{ textAlign: 'center', marginBottom: '40px' }}>
                <h1 style={{ fontSize: '2.5rem', fontWeight: 'bold', background: 'linear-gradient(to right, #6366f1, #a855f7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0 }}>
                    Pycoustics Processor
                </h1>
                <p style={{ color: '#a1a1aa' }}>Real-time Audio DSP & Analysis</p>
                <div style={{ marginTop: '10px' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', borderRadius: '12px', background: isConnected ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)', color: isConnected ? '#10b981' : '#ef4444', fontSize: '12px' }}>
                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'currentColor' }}></div>
                        {isConnected ? 'System Online' : 'Disconnected'}
                    </span>
                </div>
            </header>

            {!started ? (
                <div style={{ textAlign: 'center', marginTop: '100px' }}>
                    <button onClick={handleStart} style={{ padding: '16px 32px', fontSize: '18px', background: '#6366f1', color: 'white', border: 'none', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '10px', margin: '0 auto' }}>
                        <Mic size={24} /> Initialize Audio Engine
                    </button>
                </div>
            ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) 350px', gap: '40px', maxWidth: '1200px', margin: '0 auto', width: '100%', padding: '0 20px' }}>

                    {/* Main Control Deck */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

                        {/* Visualization */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            <VuMeter dbLevel={rms} />
                            <PanningViewer pan={panning} />
                            <SpectrumAnalyzer data={spectrum} />
                        </div>

                        {/* DSP Controls */}
                        <div style={{ background: '#1e1e1e', padding: '24px', borderRadius: '16px', border: '1px solid #333' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
                                <Sliders size={20} color="#6366f1" />
                                <h2 style={{ margin: 0, fontSize: '18px' }}>DSP Parameters</h2>
                            </div>

                            <div style={{ display: 'grid', gap: '20px' }}>
                                {/* Gain */}
                                <div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '14px' }}>
                                        <span>Input Gain</span>
                                        <span style={{ color: '#6366f1' }}>{gain.toFixed(1)} dB</span>
                                    </div>
                                    <input
                                        type="range" min="0" max="60" step="0.1"
                                        value={gain} onChange={e => setGain(parseFloat(e.target.value))}
                                        style={{ width: '100%', accentColor: '#6366f1' }}
                                    />
                                </div>

                                {/* Integration Time */}
                                <div style={{ paddingTop: '20px', borderTop: '1px solid #333' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '14px' }}>
                                        <span>Integration Time (Seconds)</span>
                                        <span style={{ color: '#6366f1' }}>{integrationTime.toFixed(2)}s</span>
                                    </div>
                                    <input
                                        type="range" min="0" max="2" step="0.05"
                                        value={integrationTime} onChange={e => setIntegrationTime(parseFloat(e.target.value))}
                                        style={{ width: '100%', accentColor: '#6366f1' }}
                                    />
                                    <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                                        Higher values = smoother visualization, but slower
                                    </div>
                                </div>

                                {/* Filter */}
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', paddingTop: '20px', borderTop: '1px solid #333' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                        <span>Low-Pass Filter</span>
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                                            <input type="checkbox" checked={filterEnabled} onChange={e => setFilterEnabled(e.target.checked)} />
                                            Enable
                                        </label>
                                    </div>
                                    <div style={{ opacity: filterEnabled ? 1 : 0.5, pointerEvents: filterEnabled ? 'auto' : 'none', transition: 'opacity 0.2s' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '14px' }}>
                                            <span>Cutoff Frequency</span>
                                            <span style={{ color: '#6366f1' }}>{cutoff} Hz</span>
                                        </div>
                                        <input
                                            type="range" min="100" max="5000" step="100"
                                            value={cutoff} onChange={e => setCutoff(parseFloat(e.target.value))}
                                            style={{ width: '100%', accentColor: '#6366f1' }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Transport */}
                        <div style={{ display: 'flex', gap: '20px' }}>
                            {!isRecording ? (
                                <button onClick={startRecording} style={{ flex: 1, padding: '20px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '12px', fontSize: '16px', fontWeight: 'bold', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px' }}>
                                    <div style={{ width: '12px', height: '12px', background: 'white', borderRadius: '50%' }}></div>
                                    Start Recording
                                </button>
                            ) : (
                                <button onClick={stopRecording} style={{ flex: 1, padding: '20px', background: '#333', color: '#ef4444', border: '1px solid #ef4444', borderRadius: '12px', fontSize: '16px', fontWeight: 'bold', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px' }}>
                                    <Square size={16} fill="currentColor" />
                                    Stop Recording
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Sidebar / Library */}
                    <div style={{ background: '#1e1e1e', borderRadius: '16px', padding: '20px', height: 'min-content' }}>
                        <h3 style={{ margin: '0 0 20px 0', fontSize: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <Save size={18} /> Recent Sessions
                        </h3>

                        <audio ref={audioRef} controls style={{ width: '100%', marginBottom: '15px' }} />

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '500px', overflowY: 'auto' }}>
                            {recordings.length === 0 && <span style={{ color: '#555', fontSize: '14px', textAlign: 'center', padding: '20px' }}>No recordings yet</span>}
                            {recordings.map(rec => (
                                <div key={rec.id} style={{ background: rec.filename === playingFile ? 'rgba(99, 102, 241, 0.2)' : '#27272a', padding: '12px', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => playRecording(rec.filename)}>
                                    <div style={{ overflow: 'hidden' }}>
                                        <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{rec.filename}</div>
                                        <div style={{ fontSize: '11px', color: '#71717a' }}>
                                            {new Date(rec.timestamp).toLocaleTimeString()} • {rec.duration_seconds.toFixed(1)}s
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', gap: '5px' }}>
                                        <a href={`${apiUrl}/recordings/${rec.filename}`} download onClick={(e) => e.stopPropagation()} style={{ color: 'inherit', display: 'flex', padding: '4px' }}>
                                            <Download size={16} />
                                        </a>
                                        <button onClick={(e) => deleteRecording(e, rec.filename)} style={{ padding: '4px', background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer' }}>
                                            <Trash2 size={16} />
                                        </button>
                                        <button style={{ padding: '4px', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}>
                                            <Play size={16} fill={rec.filename === playingFile ? "currentColor" : "none"} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                </div>
            )}
        </div>
    );
}

export default App;
