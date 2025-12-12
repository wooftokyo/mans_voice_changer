# Male Voice Changer

A tool for pitch-shifting male voices in videos. Detects male voices using AI and lowers their pitch.

## Features

### Automatic Processing
- **AI Voice Detection (Recommended)**: CNN (inaSpeechSegmenter) for high-accuracy gender detection (95-98%)
- **Simple Pitch Detection**: Lightweight, fast processing (70-80% accuracy)
- **Double Check**: Additional verification for improved accuracy

### Waveform Editor (Manual Editing)
- **WaveSurfer.js**: Professional-grade waveform display
- **Timeline**: Time-axis navigation
- **Zoom**: Precise editing of small regions
- **Multiple Region Selection**: Process multiple regions at once
- **Pitch Up/Down**: Different pitch settings per region
- **Scroll Controls**:
  - Mac: Swipe up/down = Zoom, Swipe left/right = Scroll
  - Windows: Scroll wheel = Zoom, Shift+Scroll = Scroll

### Project Management
- **History**: Auto-save processed projects (max 20)
- **Restore**: Return to any previous processing state
- **Download**: Separate MP4 (video) and WAV (audio) downloads

## Requirements

- Python 3.10+
- Node.js 18+ (for frontend development)
- ffmpeg

## Quick Start

### Production Mode

```bash
# Install Python dependencies
pip install -r requirements.txt

# Build frontend (first time or after changes)
cd frontend && npm install && npm run build && cd ..

# Start server
python voice_changer_web.py

# Open http://localhost:5003
```

### Development Mode

```bash
# Terminal 1: Start Flask API
python voice_changer_web.py

# Terminal 2: Start Vite dev server
cd frontend && npm run dev

# Open http://localhost:5173 (Vite with hot reload)
```

### Windows (Batch Files)

1. `setup.bat` - First time setup (5-10 minutes)
2. `start.bat` - Start the server
3. Browser opens http://localhost:5003 automatically

### Mac / Linux

```bash
# Install dependencies
brew install python3 ffmpeg

# Install Python packages
pip3 install -r requirements.txt

# Build frontend
cd frontend && npm install && npm run build && cd ..

# Start server
python3 voice_changer_web.py
```

## Architecture

```
mans_voice_changer/
├── frontend/           # React SPA (Vite + shadcn/ui)
│   ├── src/
│   │   ├── features/   # Feature modules
│   │   ├── components/ # UI components
│   │   └── lib/        # Utilities & API client
│   └── package.json
├── static/             # Built frontend (generated)
├── voice_changer_web.py # Flask API server
├── voice_changer.py    # Audio processing logic
└── requirements.txt
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload and process video |
| `/upload_for_editor` | POST | Upload for manual editing |
| `/status/<task_id>` | GET | Get processing status |
| `/apply_manual_pitch` | POST | Apply pitch to regions |
| `/download/<task_id>` | GET | Download processed file |
| `/audio/<task_id>` | GET | Get audio for waveform |

## Processing Modes

### AI Voice Detection (Recommended)
- inaSpeechSegmenter (CNN) for speaker gender detection
- Automatically identifies male/female voices
- Double check option for improved accuracy
- Processing time: 1-2x video length

### Simple Mode
- Segment-based pitch detection
- Pitch below threshold = male voice
- Processing time: 0.5-1x video length

## Settings

| Setting | Description | Default |
|---------|-------------|---------|
| Pitch Shift | Semitones (-12 to +12) | -3 |
| Segment Length | Detection unit (simple mode) | 0.5s |
| Male Threshold | Frequencies below this = male | 165Hz |

## Keyboard Shortcuts (Waveform Editor)

| Key | Function |
|-----|----------|
| Space | Play/Pause |
| Delete/Backspace | Remove selected region |

## Troubleshooting

### "Python not found"
- Install Python and add to PATH
- Windows: Check "Add Python to PATH" during installation

### "ffmpeg not found"
- Windows: `winget install ffmpeg`
- Mac: `brew install ffmpeg`

### Processing takes too long
- AI detection takes longer (5-10 min for 5 min video)
- High CPU usage is normal during processing

### Port in use
- Another app is using port 5003
- Change port in voice_changer_web.py

## Command Line

```bash
# Basic usage
python voice_changer.py input.mp4

# Specify output
python voice_changer.py input.mp4 -o output.mp4

# Change pitch shift (default: -3 semitones)
python voice_changer.py input.mp4 -p -5
```

## License

MIT License
