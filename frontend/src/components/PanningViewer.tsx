import { useEffect, useRef } from 'react';

interface PanningViewerProps {
    pan: number; // -1.0 (Left) to 1.0 (Right)
}

export const PanningViewer = ({ pan }: PanningViewerProps) => {
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

        // Center Line (Vertical)
        ctx.beginPath();
        ctx.moveTo(width / 2, 0);
        ctx.lineTo(width / 2, height);
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Horizontal Axis
        const centerY = height / 2;
        ctx.beginPath();
        ctx.moveTo(10, centerY);
        ctx.lineTo(width - 10, centerY);
        ctx.strokeStyle = '#555';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw L / R text
        ctx.fillStyle = '#666';
        ctx.font = '10px sans-serif';
        ctx.fillText('L', 10, centerY - 10);
        ctx.fillText('R', width - 20, centerY - 10);

        // Map Pan to X coordinate
        // pan: -1 -> 10 + radius
        // pan: 1 -> width - 10 - radius
        const padding = 20;
        const trackWidth = width - 2 * padding;

        // Normalize pan to 0-1
        const normalizedPan = (pan + 1) / 2;
        const x = padding + (normalizedPan * trackWidth);
        const y = centerY;

        // Draw Indicator Point
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, 2 * Math.PI);
        ctx.fillStyle = '#10b981'; // Emerald Green
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Glow effect
        ctx.shadowBlur = 10;
        ctx.shadowColor = '#10b981';
        ctx.fill();
        ctx.shadowBlur = 0;

    }, [pan]);

    return (
        <div style={{ padding: '10px', background: '#1e1e1e', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.3)' }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#a1a1aa' }}>Stereo Panning</h3>
            <canvas ref={canvasRef} width={600} height={50} style={{ borderRadius: '4px', width: '100%' }} />
        </div>
    );
};
