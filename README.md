# Hallmark Record - Multi-Input Recording & Editing Application

A professional multi-input recording and editing application that allows you to record from multiple cameras, microphones, screens, and monitors simultaneously, then edit them in a simple-to-use interface.

## Features

### Recording
- **Multiple Camera Support**: Record from multiple USB cameras or webcams simultaneously
- **Multi-Microphone Recording**: Capture audio from multiple microphones at once
- **Multi-Monitor Screen Recording**: Record from all your monitors/screens independently
- **Synchronized Recording**: All inputs are recorded in sync for easy editing
- **Background Recording**: FFmpeg-based recording runs efficiently in the background

### Editing
- **Web-Based Editor**: Simple, intuitive browser-based editing interface
- **Trim Videos**: Cut videos to specific start and end times
- **Merge Multiple Videos**: Combine videos in various layouts:
  - Grid layout (2x2, 3x3, etc.)
  - Horizontal (side-by-side)
  - Vertical (stacked)
  - Concatenate (one after another)
- **Add Audio Tracks**: Overlay audio from microphones onto video recordings
- **Export Options**: Export in multiple formats (MP4, WebM, AVI) with quality presets
- **Session Management**: Organize recordings by session

## Installation

### Prerequisites
1. **Python 3.8 or higher**
2. **FFmpeg**: The application uses FFmpeg from the cloned hallmark-scribble repository, or you can install it separately:
   - Download from: https://ffmpeg.org/download.html
   - Add to system PATH or place in application directory

### Setup Steps

1. **Clone or navigate to the project directory**:
   ```bash
   cd "c:\Users\AGough\Hallmark University\IT Services - Documents\Scripts + Tools\Hallmark Record"
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify FFmpeg is available**:
   The application will automatically use FFmpeg from the hallmark-scribble repository if present.

## Usage

### Starting the Application

Run the main GUI application:
```bash
python main.py
```

### Recording Workflow

1. **Select Devices**:
   - Click "Refresh Devices" to detect all available cameras, microphones, and monitors
   - Select the devices you want to record from (you can select multiple)
   - Use "Select All" buttons to quickly select all devices in a category

2. **Start Recording**:
   - Click "🔴 Start Recording"
   - The application will begin recording from all selected devices simultaneously
   - Monitor the recording log for status updates

3. **Stop Recording**:
   - Click "⏹️ Stop Recording" when finished
   - All recordings will be saved to the `outputs/session_TIMESTAMP/` directory

### Editing Workflow

1. **Open Editor**:
   - Click "✂️ Open Editor" in the main application
   - The web-based editor will open in your default browser at http://localhost:5000

2. **Select Session**:
   - In the "Sessions" tab, you'll see all your recording sessions
   - Click on a session to view all recorded files

3. **Edit Individual Files** (Edit Tab):
   - Select a session and file
   - Preview the video/audio
   - Set trim start and end times
   - Click "Trim Video" to create a trimmed version

4. **Merge Multiple Videos** (Merge Tab):
   - Select a session
   - Click on multiple files to select them
   - Choose a layout (Grid, Horizontal, Vertical, or Concatenate)
   - Enter an output name
   - Click "Merge Videos"

5. **Export Final Video** (Export Tab):
   - Select a session and the file to export
   - Choose format (MP4, WebM, AVI)
   - Select quality preset (High, Medium, Low)
   - Click "Export Video"

## Project Structure

```
Hallmark Record/
├── main.py                          # Main GUI application
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
│
├── recorder/                        # Recording modules
│   └── multi_input_recorder.py     # Multi-input recorder class
│
├── editor/                          # Editing modules
│   ├── video_editor.py             # Flask-based editor server
│   └── templates/
│       └── editor.html             # Web editor interface
│
├── outputs/                         # Recording output directory
│   └── session_TIMESTAMP/          # Each recording session
│       ├── camera_1_*.mp4
│       ├── mic_1_*.wav
│       └── monitor_1_*.mp4
│
└── hallmark-scribble/              # Cloned repository (contains FFmpeg)
    └── shared/
        └── ffmpeg/
            └── bin/
                └── ffmpeg.exe
```

## Features in Detail

### Multi-Input Recorder
The `multi_input_recorder.py` module provides:
- Device detection for cameras, microphones, and monitors
- Simultaneous recording from all selected devices
- Automatic file naming and organization
- Thread-safe recording management
- Graceful shutdown of all recording processes

### Video Editor
The web-based editor provides:
- Session management and file browsing
- Real-time video/audio preview
- Timeline-based editing (trim, cut)
- Multi-video merging with custom layouts
- Audio track management
- High-quality export options

## Technical Details

### Recording Technology
- **FFmpeg**: Industry-standard multimedia framework
- **DirectShow (Windows)**: Native Windows API for device access
- **GDIGrab**: Windows screen capture API
- **H.264 Encoding**: Efficient video compression

### Supported Formats
- **Input**: Any camera/microphone/screen recognized by DirectShow
- **Recording**: MP4 (H.264), WAV (audio)
- **Export**: MP4, WebM, AVI

### System Requirements
- **OS**: Windows 10 or higher (uses Windows-specific APIs)
- **RAM**: 8GB+ recommended for multi-stream recording
- **Storage**: Fast SSD recommended for multiple simultaneous recordings
- **CPU**: Multi-core processor recommended

## Troubleshooting

### No Devices Found
- Ensure cameras and microphones are properly connected
- Try unplugging and reconnecting devices
- Click "Refresh Devices" after connecting new hardware

### Recording Failed to Start
- Check that FFmpeg is available (application will show path in logs)
- Ensure no other application is using the cameras/microphones
- Try recording from fewer devices simultaneously

### Editor Won't Open
- Check if port 5000 is already in use
- Ensure Flask is properly installed: `pip install Flask`
- Check the application log for error messages

### Video Quality Issues
- Adjust recording resolution in the code (default is 1280x720 for cameras)
- Use "High" quality preset when exporting
- Ensure sufficient disk space for high-quality recordings

## Advanced Configuration

### Customizing Recording Settings
Edit `recorder/multi_input_recorder.py`:
- Camera resolution: Change `-video_size` parameter
- Frame rate: Modify `-framerate` value
- Audio quality: Adjust audio encoding parameters

### Custom Export Presets
Edit `editor/video_editor.py`:
- Add custom quality presets in the `quality_settings` dictionary
- Modify codec settings for different output formats

## Credits

Built using code from the [hallmark-scribble](https://github.com/agough77/hallmark-scribble) repository, specifically the video recording modules from the `shared/recorder/` directory.

## License

This project uses components from hallmark-scribble which is licensed under the GNU General Public License v3.0.

## Support

For issues or questions:
1. Check the application logs in the main window
2. Review the FFmpeg output in the session directory
3. Ensure all dependencies are properly installed

## Future Enhancements

Potential improvements:
- [ ] Audio mixing and volume control
- [ ] Real-time preview during recording
- [ ] Effects and filters
- [ ] Cloud storage integration
- [ ] Automatic synchronization of audio/video streams
- [ ] GPU-accelerated encoding
- [ ] Mobile app for remote control
- [ ] Live streaming support
