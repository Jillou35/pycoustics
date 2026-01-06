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
    const processorRef = useRef<ScriptProcessorNode | null>(null);
    const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);

    const connectWebSocket = useCallback(() => {
        if (socketRef.current?.readyState === WebSocket.OPEN) return;

        const wsUrl = import.meta.env.VITE_WS_URL || "ws://localhost:8000";
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

            audioContextRef.current = new AudioContext({ sampleRate: 44100 });
            sourceRef.current = audioContextRef.current.createMediaStreamSource(stream);

            // Use ScriptProcessor for raw PCM access (bufferSize=1024 ~ 23ms latency)
            // 2 input channels, 2 output channels
            processorRef.current = audioContextRef.current.createScriptProcessor(1024, 2, 2);

            processorRef.current.onaudioprocess = (e) => {
                if (socketRef.current?.readyState === WebSocket.OPEN) {
                    // Get float data
                    // We need to interleave L and R channels
                    const inputL = e.inputBuffer.getChannelData(0);
                    const inputR = e.inputBuffer.numberOfChannels > 1 ? e.inputBuffer.getChannelData(1) : inputL; // Duplicate if mono source

                    if (inputL.length !== inputR.length) return; // Should not happen

                    const length = inputL.length;
                    const pcmData = new Int16Array(length * 2);

                    let pcmIndex = 0;
                    for (let i = 0; i < length; i++) {
                        // Channel L
                        let sL = Math.max(-1, Math.min(1, inputL[i]));
                        pcmData[pcmIndex++] = sL < 0 ? sL * 0x8000 : sL * 0x7FFF;

                        // Channel R
                        let sR = Math.max(-1, Math.min(1, inputR[i]));
                        pcmData[pcmIndex++] = sR < 0 ? sR * 0x8000 : sR * 0x7FFF;
                    }

                    socketRef.current.send(pcmData.buffer);
                }
            };

            sourceRef.current.connect(processorRef.current);
            processorRef.current.connect(audioContextRef.current.destination); // Needed for Chrome to activate it

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
