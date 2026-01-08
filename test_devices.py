"""
Test script for device detection
"""
from recorder.multi_input_recorder import MultiInputRecorder

print("=" * 50)
print("Testing Hallmark Record Device Detection")
print("=" * 50)
print()

# Initialize recorder
r = MultiInputRecorder()
print(f"FFmpeg path: {r.ffmpeg_path}")
print()

# Test cameras
print("Detecting Cameras...")
cameras = r.list_video_devices()
print(f"Found {len(cameras)} camera(s):")
for i, cam in enumerate(cameras):
    print(f"  {i+1}. {cam}")
print()

# Test microphones
print("Detecting Microphones...")
mics = r.list_audio_devices()
print(f"Found {len(mics)} microphone(s):")
for i, mic in enumerate(mics):
    print(f"  {i+1}. {mic}")
print()

# Test monitors
print("Detecting Monitors...")
monitors = r.list_monitors()
print(f"Found {len(monitors)} monitor(s):")
for i, mon in enumerate(monitors):
    primary = " (Primary)" if mon['is_primary'] else ""
    print(f"  {i+1}. {mon['name']} - {mon['width']}x{mon['height']} at ({mon['x']}, {mon['y']}){primary}")
print()

print("=" * 50)
print("Device detection test complete!")
print("=" * 50)

if not cameras and not mics:
    print()
    print("NOTE: FFmpeg is not installed or not accessible.")
    print("To install FFmpeg:")
    print("1. Download from: https://ffmpeg.org/download.html")
    print("2. Add to system PATH")
    print("   OR")
    print("3. Place ffmpeg.exe in: hallmark-scribble/shared/ffmpeg/bin/")
    print()
    print("Without FFmpeg, you can still test the monitor detection,")
    print("but camera and microphone recording will not work.")
