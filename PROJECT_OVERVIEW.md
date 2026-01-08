# Hallmark Record - Project Overview

## 🎯 What This Application Does

Hallmark Record is a comprehensive multi-input recording and editing application that allows you to:

1. **Record simultaneously** from:
   - Multiple USB cameras/webcams
   - Multiple microphones
   - Multiple monitors/screens (including secondary displays)

2. **Edit your recordings** with:
   - Video trimming and cutting
   - Multi-video merging (grid, side-by-side, stacked)
   - Audio track overlay
   - Professional export with quality presets

3. **Manage sessions** with:
   - Automatic file organization
   - Session browsing
   - Preview capabilities

## 📦 What's Included

### Core Application Files
- **main.py** - Main GUI application (PyQt5-based)
- **START_RECORDER.bat** - Quick launch for recording app
- **START_EDITOR.bat** - Quick launch for web editor
- **INSTALL.bat** - One-click dependency installation

### Recording Module (`recorder/`)
- **multi_input_recorder.py** - Core recording engine
  - Device detection (cameras, mics, monitors)
  - Simultaneous multi-stream recording
  - FFmpeg integration

### Editing Module (`editor/`)
- **video_editor.py** - Flask web server
- **templates/editor.html** - Web-based editing interface
  - Session management
  - Video trimming
  - Multi-video merging
  - Export functionality

### Documentation
- **README.md** - Complete documentation
- **QUICK_START.md** - Getting started guide
- **This file** - Project overview

### Integration
- **hallmark-scribble/** - Cloned repository
  - Contains FFmpeg binaries
  - Provides video recording foundations

## 🔧 Technology Stack

### Frontend
- **PyQt5** - Desktop GUI framework
- **HTML/CSS/JavaScript** - Web-based editor
- **Bootstrap-inspired styling** - Modern, responsive UI

### Backend
- **Python 3.8+** - Core language
- **Flask** - Web server for editor
- **FFmpeg** - Video/audio processing
- **DirectShow** - Windows device access
- **GDIGrab** - Screen capture API

### Dependencies
```
PyQt5>=5.15.0    # Desktop GUI
Flask>=2.3.0     # Web server
pywin32>=305     # Windows API access
```

## 📂 Project Structure

```
Hallmark Record/
│
├── 🚀 Quick Start
│   ├── INSTALL.bat           # Install dependencies
│   ├── START_RECORDER.bat    # Launch recorder
│   ├── START_EDITOR.bat      # Launch editor
│   └── QUICK_START.md        # Quick guide
│
├── 📱 Main Application
│   └── main.py               # GUI application
│
├── 🎥 Recorder Module
│   └── recorder/
│       ├── multi_input_recorder.py
│       └── __init__.py
│
├── ✂️ Editor Module
│   └── editor/
│       ├── video_editor.py
│       ├── __init__.py
│       └── templates/
│           └── editor.html
│
├── 💾 Outputs
│   └── outputs/
│       ├── README.md
│       └── session_*/       # Recording sessions
│
├── 📚 Documentation
│   ├── README.md            # Full documentation
│   ├── QUICK_START.md       # Quick guide
│   └── PROJECT_OVERVIEW.md  # This file
│
├── 🔧 Configuration
│   └── requirements.txt     # Python dependencies
│
└── 🎬 Hallmark Scribble
    └── hallmark-scribble/   # Cloned repo with FFmpeg
        └── shared/
            └── ffmpeg/
                └── bin/
                    └── ffmpeg.exe
```

## 🎯 Key Features Explained

### 1. Multi-Device Recording
**Problem Solved**: Traditional screen recorders only capture one source at a time.

**Solution**: Records all selected devices simultaneously in separate files, allowing maximum flexibility during editing.

**Technical Implementation**:
- Each device gets its own FFmpeg process
- Processes run in parallel with synchronized start times
- Individual files prevent data loss if one stream fails

### 2. Web-Based Editor
**Problem Solved**: Desktop video editors are complex and resource-intensive.

**Solution**: Simple, browser-based interface focused on common tasks.

**Technical Implementation**:
- Flask server provides REST API
- HTML5 video/audio elements for preview
- FFmpeg command generation for processing
- No complex timeline or tracks - just simple operations

### 3. Flexible Merging
**Problem Solved**: Combining multiple video sources requires expensive software.

**Solution**: Multiple layout options with automatic scaling and positioning.

**Technical Implementation**:
- FFmpeg filter_complex for layouts
- hstack/vstack for arrangements
- Automatic dimension adjustment for H.264 compatibility

## 🔄 Workflow Examples

### Example 1: Tutorial Recording
```
1. Select: Primary Monitor + Webcam + Microphone
   ↓
2. Record 10-minute tutorial
   ↓
3. Output: 
   - monitor_1_Primary_Monitor.mp4 (screen)
   - camera_1_Webcam.mp4 (face)
   - mic_1_Microphone.wav (voice)
   ↓
4. In Editor:
   - Merge monitor + camera (picture-in-picture grid)
   - Trim intro/outro
   - Export high quality MP4
```

### Example 2: Multi-Camera Recording
```
1. Select: Camera 1 + Camera 2 + Camera 3
   ↓
2. Record event from multiple angles
   ↓
3. Output: 3 separate camera files
   ↓
4. In Editor:
   - Preview all angles
   - Choose best angle or merge in grid
   - Trim to key moments
   - Export final video
```

### Example 3: Conference Capture
```
1. Select: All Monitors + Multiple Mics
   ↓
2. Record presentation across dual monitors
   ↓
3. Output: 2 monitor recordings + audio files
   ↓
4. In Editor:
   - Merge monitors side-by-side
   - Select best audio source
   - Export for sharing
```

## 🚀 Getting Started

1. **Install** - Run `INSTALL.bat`
2. **Record** - Run `START_RECORDER.bat`
3. **Edit** - Click "Open Editor" or run `START_EDITOR.bat`

See QUICK_START.md for detailed steps.

## 🎓 Learning Resources

- **FFmpeg Documentation**: https://ffmpeg.org/documentation.html
- **PyQt5 Documentation**: https://www.riverbankcomputing.com/static/Docs/PyQt5/
- **Flask Documentation**: https://flask.palletsprojects.com/

## 🔮 Future Enhancements

Potential features for future versions:
- Real-time preview during recording
- Audio mixing and normalization
- Effects and transitions
- GPU-accelerated encoding
- Cloud storage integration
- Live streaming support
- Mobile remote control
- Automatic scene detection
- AI-powered auto-editing

## 📊 Performance Considerations

### Disk Space
- 1GB per 10 minutes of HD video
- Use SSD for best performance
- Regular cleanup of test recordings

### CPU Usage
- Each recording stream uses CPU
- Limit simultaneous recordings based on system
- Close other applications during recording

### Memory
- 8GB RAM minimum recommended
- 16GB+ for multiple HD streams

## 🐛 Known Limitations

1. **Windows Only**: Uses Windows-specific APIs (DirectShow, GDIGrab)
2. **FFmpeg Required**: Must have FFmpeg available
3. **Synchronization**: Manual sync required for multi-source editing
4. **Format Support**: Limited to H.264/AAC output
5. **Real-time**: No live preview during recording

## 🤝 Contributing

This project uses code from hallmark-scribble. When improving:
- Test with multiple device types
- Document any FFmpeg command changes
- Update README with new features
- Keep the interface simple and intuitive

## 📄 License

Uses components from hallmark-scribble (GPL-3.0).

## ✨ Credits

Built by integrating the video recording capabilities from the [hallmark-scribble](https://github.com/agough77/hallmark-scribble) repository, specifically leveraging the FFmpeg-based recording modules.

---

**Ready to start recording?** Run `START_RECORDER.bat` or see QUICK_START.md!
