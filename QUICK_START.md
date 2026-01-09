# Quick Start Guide - Hallmark Record

## 🚀 Getting Started in 3 Steps

### Step 1: Install Dependencies
Double-click `INSTALL.bat` to install all required Python packages.

### Step 2: Start Recording
1. Double-click `START_RECORDER.bat` to launch the main application
2. Click "🔄 Refresh Devices" to detect your cameras, microphones, and monitors
3. Select the devices you want to record from
4. Click "🔴 Start Recording"
5. When done, click "⏹️ Stop Recording"

### Step 3: Edit Your Recordings
1. In the main app, click "✂️ Open Editor" (or run `START_EDITOR.bat`)
2. Browser opens at http://localhost:5500
3. Select your session from the list
4. Use the tabs to:
   - **Edit**: Trim individual videos
   - **Merge**: Combine multiple videos in different layouts
   - **Export**: Create final output with quality settings

## 📁 Where Are My Files?

All recordings are saved in:
```
outputs/session_TIMESTAMP/
```

Each session contains:
- `camera_1_[name].mp4` - Camera recordings
- `mic_1_[name].wav` - Microphone recordings  
- `monitor_1_[name].mp4` - Screen recordings

## 🎯 Common Use Cases

### Recording a Presentation
1. Select: Primary Monitor + Microphone
2. Record your screen with narration
3. Edit: Trim beginning/end, export as MP4

### Multi-Camera Setup
1. Select: Multiple Cameras + Multiple Monitors
2. Record all angles simultaneously
3. Edit: Merge in grid layout for multi-view

### Tutorial Recording
1. Select: Screen + Webcam + Microphone
2. Record screen, face, and voice
3. Edit: Picture-in-picture layout

### Meeting Recording
1. Select: All Monitors + Microphone
2. Capture entire workspace
3. Edit: Trim to relevant portions

## ⚡ Pro Tips

- **Test First**: Record a 5-second test before long sessions
- **Storage**: Ensure you have enough disk space (1GB per 10 min of video)
- **Quality**: Use "High" export quality for final outputs
- **Backup**: Copy important sessions to external storage
- **Multi-Monitor**: Each monitor records independently for flexibility

## 🔧 Keyboard Shortcuts in Editor

- **Space**: Play/Pause preview
- **Arrow Keys**: Navigate timeline
- **M**: Mute/Unmute
- **F**: Fullscreen preview

## ❓ Troubleshooting

**Can't see my camera?**
- Unplug and reconnect
- Close other apps using the camera
- Click "Refresh Devices"

**Recording is laggy?**
- Record fewer devices simultaneously
- Check CPU usage
- Use faster storage (SSD)

**Editor won't open?**
- Check if port 5500 is in use
- Run START_EDITOR.bat manually
- Check firewall settings

**No sound in recording?**
- Select the correct microphone
- Check Windows sound settings
- Test microphone in other apps first

## 📞 Need Help?

1. Check the full README.md for detailed documentation
2. Review application logs in the main window
3. Check the ffmpeg_output.log in your session folder

## 🎉 Happy Recording!
