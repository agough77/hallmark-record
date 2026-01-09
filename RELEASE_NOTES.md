# Hallmark Record v1.0.0 Release Notes

## 🎉 Initial Release

Multi-input recording and editing application for Windows that allows simultaneous recording from multiple cameras, microphones, and monitors with a professional timeline-based editor.

## ✨ Features

### Recording Application
- **Multi-device recording**: Record from multiple cameras, microphones, and monitors simultaneously
- **Device management**: Easy selection and configuration of input devices
- **Folder selection**: Choose where recordings are saved (defaults to Downloads/Hallmark Record)
- **Background recording**: Efficient FFmpeg-based recording engine

### Timeline Editor
- **Clipchamp-style interface**: Professional, intuitive timeline editor
- **Auto-load sessions**: Automatically loads all recordings into timeline
- **Visual overlay positioning**: Drag and resize picture-in-picture overlays
- **Timeline zoom controls**: 0.5x to 10x zoom for precise editing
- **Click-to-seek**: Click anywhere on timeline to jump to that point
- **Visual trim markers**: Draggable green/red markers for precise trimming
- **Split at playhead**: Split clips at current position
- **Audio recording**: Record additional audio directly from editor
- **File management**: Delete unwanted files with confirmation
- **Export options**: Multiple format and quality presets

## 📦 Installation Options

### Option 1: Complete Package (Recommended)
Download the all-in-one package that includes both recorder and editor with all dependencies:

1. Download `HallmarkRecord_v1.0.0_Complete.zip` (268 MB)
2. Extract to your desired location (e.g., `C:\Program Files\HallmarkRecord\`)
3. Double-click `Start Recorder.bat` to record
4. Double-click `Start Editor.bat` to edit (automatically opens browser)

**No Python installation required!** Everything is bundled including FFmpeg.

**What's in the package:**
- Recorder Application (Hallmark Recorder.exe)
- Editor Application (Hallmark Editor.exe)
- Quick launch batch files
- Complete documentation (README.txt)
- MIT License

### Option 2: Manual Installation (Developers)
Clone the repository and install Python dependencies:

```bash
git clone https://github.com/agough77/hallmark-record.git
cd hallmark-record
pip install -r requirements.txt
python main.py  # For recorder
python editor/video_editor.py  # For editor
```

## 🔧 System Requirements

- **OS**: Windows 10 or later (64-bit)
- **RAM**: 8GB minimum, 16GB recommended for multiple HD streams
- **Storage**: SSD recommended, ~1GB per 10 minutes of HD video
- **CPU**: Multi-core processor recommended for multiple simultaneous recordings

## 📖 Quick Start

1. **Launch Recorder**: Run `Hallmark Recorder.exe`
2. **Select devices**: Check cameras, microphones, and monitors you want to record
3. **Choose folder**: Select where to save recordings
4. **Start recording**: Click "Start Recording"
5. **Stop recording**: Click "Stop Recording" when done
6. **Open editor**: Click "Open Editor" or run `Hallmark Editor.exe`
7. **Edit timeline**: Use drag-and-drop, trim, overlay, and export

## 🐛 Known Issues

- Inno Setup installer not yet available (use standalone executables for now)
- Editor must be launched separately from recorder (no automatic integration yet)
- Some Windows 11 systems may show SmartScreen warning (click "More info" → "Run anyway")

## 🔜 Coming Soon

- Full installer package with Inno Setup
- Text overlay capabilities
- Transition effects
- Advanced audio mixing
- GPU-accelerated encoding
- Cloud storage integration

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Credits

Built using FFmpeg for video/audio processing and leveraging code from the hallmark-scribble project.

## 📞 Support

For issues, questions, or feature requests, please visit:
https://github.com/agough77/hallmark-record/issues

---

**Enjoy recording!** 🎥🎬
