
# Pycoustics - Audio DSP & Visualization Platform

A robust real-time Audio DSP application demonstrating mastery of Python (FastAPI), React, and binary data streaming. Built for performance, testability, and easy deployment.

## Features

### 🎧 Real-time Processing
- **Low-Latency Streaming**: 16-bit PCM streaming via optimized WebSockets.
- **DSP Engine**: NumPy/SciPy pipeline supporting:
    - **Gain/Volume Control**: Adjustable input amplification (up to 60dB) with safe signal clipping.
    - **Low-pass Filtering**: Real-time Butterworth filter with customizable cutoff frequency and state continuity.
    - **Smoothing**: Adjustable integration time for visual responsiveness.

### 📊 Advanced Visualization
- **Multi-View Dashboard**:
    - **Waveform**: Real-time oscilloscope-style time domain view.
    - **Spectrum Analyzer**: Frequency domain visualization with logarithmic scaling.
    - **VuMeter**: Accurate RMS level monitoring with peak detection.
    - **Panning**: Stereo balance visualization.
- **Canvas API**: High-performance rendering for smooth 60fps animations.

### 💾 Recording & Sessions
- **Session Isolation**: Unique session IDs ensure privacy and isolation between concurrent users.
- **Persistence**: 
    - Asynchronous recording to disk (WAV format).
    - SQLite database for metadata management.
    - Auto-cleanup of session files upon disconnect.
- **Management**: UI controls to start/stopping recording, download files, and delete recordings.

### 🚀 Deployment & DevOps
- **Dockerized**: specific `Dockerfile` for backend (Python 3.10) and frontend (Vite/Nginx).
- **Environment Config**: Flexible `docker-compose.yml` supporting:
    - Build-time args (`VITE_API_URL`, `VITE_WS_URL`) for frontend.
    - Runtime envs (`FRONTEND_URL`) for backend.
    - Port configuration for both services in .env file at root directory (`FRONTEND_PORT=3000`, `BACKEND_PORT=8000`)
    - Compatible with **Coolify** and other PaaS via variable substitution.

### 🛡️ Quality Assurance
- **Comprehensive Testing**: >90% code coverage.
    - **Unit Tests**: `AudioProcessor` DSP logic, `AudioRecorder` file operations.
    - **Integration Tests**: WebSocket flows, REST API endpoints, error handling.
- **Type Safety**: Full Pydantic schemas and TypeScript interfaces.

## Architecture

### Backend (FastAPI + NumPy)
- **AudioPipeline**: `AudioProcessor` handles chunks with vectorization. Internal state (`zi`) prevents clicking/popping during filter changes.
- **WebSocket Protocol**: Custom JSON+Binary protocol for command/control and data streaming.
    - `init`: Handshake with sample rate/channels.
    - `start_record` / `stop_record`: Session management.
    - `set_params`: Real-time DSP parameter updates.

### Frontend (React + Vite)
- **Audio Context**: `ScriptProcessorNode` (or AudioWorklet) for consistent buffer capture.
- **Hooks**: Custom `useAudioStream` hook manages WebSocket lifecycle, auto-reconnection, and binary data marshaling.

## Setup & Run

### Using Docker (Recommended)
```bash
# 1. Start services
docker-compose up --build

# 2. Access
# Frontend: http://localhost:3000
# Backend Docs: http://localhost:8000/docs
```

### Deployment (e.g., Coolify)
Set these environment variables in your deployment dashboard:
- **Backend**: `FRONTEND_URL` (e.g., `https://my-app.com`)
- **Frontend**: `API_URL` (e.g., `https://api.my-app.com`), `WS_URL` (e.g., `wss://api.my-app.com`)

### Testing
Run the backend test suite inside Docker:
```bash
docker-compose run --rm backend pytest
```

## Tech Stack
- **Core**: Python 3.10, TypeScript 5
- **Backend**: FastAPI, NumPy, SciPy, SQLAlchemy, Pytest
- **Frontend**: React, Vite, Tailwind-style CSS, Lucide Icons
