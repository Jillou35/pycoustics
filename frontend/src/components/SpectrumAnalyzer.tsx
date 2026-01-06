
import { useEffect, useRef } from 'react';

interface SpectrumAnalyzerProps {
    data: number[]; // Array of normalized magnitudes (0-1)
}

export const SpectrumAnalyzer = ({ data }: SpectrumAnalyzerProps) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const width = canvas.width;
        const height = canvas.height;

        // Clear
        ctx.clearRect(0, 0, width, height);

        // Background
        ctx.fillStyle = '#1e1e1e';
        ctx.fillRect(0, 0, width, height);

        if (!data || data.length === 0) return;

        const barWidth = width / data.length;

        // Draw bars
        data.forEach((value, i) => {
            const barHeight = value * height;
            const x = i * barWidth;
            const y = height - barHeight;

            // Gradient
            const gradient = ctx.createLinearGradient(0, height, 0, 0);
            gradient.addColorStop(0, '#6366f1');   // Indigo
            gradient.addColorStop(1, '#a855f7');   // Purple

            ctx.fillStyle = gradient;
            ctx.fillRect(x, y, barWidth - 1, barHeight); // -1 for spacing
        });

    }, [data]);

    return (
        <div style={{ padding: '10px', background: '#1e1e1e', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.3)', marginBottom: '20px' }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#a1a1aa' }}>Real-time Spectrum</h3>
            <canvas ref={canvasRef} width={600} height={100} style={{ borderRadius: '4px', width: '100%', height: '100px' }} />
        </div>
    );
};
