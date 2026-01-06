
import { useEffect, useRef } from 'react';

interface VuMeterProps {
    dbLevel: number; // dB value, typically -60 to 0
}

export const VuMeter = ({ dbLevel }: VuMeterProps) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let normalized = (dbLevel + 60) / 60;
        normalized = Math.max(0, Math.min(1, normalized));

        const width = canvas.width;
        const height = canvas.height;

        // Clear
        ctx.clearRect(0, 0, width, height);

        // Background track
        ctx.fillStyle = '#333';
        ctx.fillRect(0, 0, width, height);

        // Gradient Bar
        const gradient = ctx.createLinearGradient(0, 0, width, 0);
        gradient.addColorStop(0, '#10b981'); // Green
        gradient.addColorStop(0.6, '#f59e0b'); // Yellow
        gradient.addColorStop(1, '#ef4444'); // Red

        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width * normalized, height);

        // Text
        ctx.fillStyle = '#fff';
        ctx.font = '20px monospace';
        ctx.fillText(`${dbLevel.toFixed(1)} dB`, 10, height / 2 + 4);

    }, [dbLevel]);

    return (
        <div style={{ padding: '10px', background: '#1e1e1e', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.3)' }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#a1a1aa' }}>Signal Level</h3>
            <canvas ref={canvasRef} width={600} height={60} style={{ borderRadius: '4px', width: '100%' }} />
        </div>
    );
};
