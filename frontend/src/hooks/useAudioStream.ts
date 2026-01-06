import { useEffect, useRef, useState, useCallback } from 'react';

interface AudioStreamHook {
    isConnected: boolean;
    isRecording: boolean;
    spectrum: number[];
    rms: number;
    panning: number;
    startAudio: () => Promise<void>;
    startRecording: () => void;
    stopRecording: () => void;
    setSettings: (gain: number, filter: boolean, cutoff: number, integrationTime: number) => void;
    lastRecording: { id: number; filename: string } | null;
    sessionId: string;
}

export const useAudioStream = (): AudioStreamHook => {
    const [isConnected, setIsConnected] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [rms, setRms] = useState(-100);
    const [spectrum, setSpectrum] = useState<number[]>([]);
    const [panning, setPanning] = useState(0);
    const [lastRecording, setLastRecording] = useState<{ id: number; filename: string } | null>(null);

    const sessionIdRef = useRef<string>(Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15));
    const socketRef = useRef<WebSocket | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const workletNodeRef = useRef<AudioWorkletNode | null>(null);
    const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);

    const connectWebSocket = useCallback(() => {
        if (socketRef.current?.readyState === WebSocket.OPEN) return;
        const wsUrl = import.meta.env.VITE_WS_URL || `ws://localhost:8000`;
        const ws = new WebSocket(`${wsUrl}/ws/audio?session_id=${sessionIdRef.current}`);

        ws.onopen = () => {
            console.log('WS Connected');
            setIsConnected(true);

            // Send initialization parameters
            const sampleRate = audioContextRef.current?.sampleRate || 44100;
            const channels = audioContextRef.current?.destination.channelCount || 2;
            ws.send(JSON.stringify({
                action: "init",
                sample_rate: sampleRate,
                channels: channels
            }));
        };

        ws.onclose = () => {
            console.log('WS Disconnected');
            setIsConnected(false);
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'meter') {
                setRms(data.rms);
                if (data.spectrum) setSpectrum(data.spectrum);
                if (data.panning !== undefined) setPanning(data.panning);
            } else if (data.type === 'recording_saved') {
                setLastRecording({ id: data.id, filename: data.filename });
                setIsRecording(false);
            }
        };

        socketRef.current = ws;
    }, []);


    const startAudio = async () => {
        if (!socketRef.current) connectWebSocket();

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: false,
                    autoGainControl: false,
                    noiseSuppression: false,
                    channelCount: 2 // Request Stereo
                }
            });

            audioContextRef.current = new AudioContext(); // Use default sample rate
            sourceRef.current = audioContextRef.current.createMediaStreamSource(stream);

            // Load the AudioWorklet module
            try {
                await audioContextRef.current.audioWorklet.addModule('/audio-processor.js');
            } catch (e) {
                console.error("Failed to load audio-processor.js", e);
                return;
            }

            // Create AudioWorkletNode
            workletNodeRef.current = new AudioWorkletNode(audioContextRef.current, 'pcm-processor', {
                outputChannelCount: [2]
            });

            // Handle messages from the processor (PCM data)
            workletNodeRef.current.port.onmessage = (event) => {
                if (socketRef.current?.readyState === WebSocket.OPEN) {
                    socketRef.current.send(event.data);
                }
            };

            sourceRef.current.connect(workletNodeRef.current);
            workletNodeRef.current.connect(audioContextRef.current.destination);

        } catch (err) {
            console.error("Error accessing microphone:", err);
        }
    };

    const startRecording = () => {
        if (socketRef.current?.readyState === WebSocket.OPEN) {
            const sampleRate = audioContextRef.current?.sampleRate || 44100;
            const channels = audioContextRef.current?.destination.channelCount || 2;
            socketRef.current.send(JSON.stringify({
                action: "start_record",
                sample_rate: sampleRate,
                channels: channels
            }));
            setIsRecording(true);
        }
    };

    const stopRecording = () => {
        if (socketRef.current?.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify({ action: "stop_record" }));
        }
    };

    const setSettings = (gain: number, filter: boolean, cutoff: number, integrationTime: number) => {
        if (socketRef.current?.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify({
                action: "set_params",
                gain,
                filter_enabled: filter,
                cutoff_freq: cutoff,
                integration_time: integrationTime
            }));
        }
    };

    // Cleanup
    useEffect(() => {
        connectWebSocket();
        return () => {
            socketRef.current?.close();
            audioContextRef.current?.close();
        };
    }, [connectWebSocket]);

    return {
        isConnected, isRecording, rms, spectrum, panning, startAudio, startRecording,
        stopRecording,
        setSettings,
        lastRecording,
        sessionId: sessionIdRef.current
    };
};
