"""
Detailed FFmpeg Device Diagnostic
"""
import subprocess
import os

ffmpeg_path = os.path.join(
    os.path.dirname(__file__),
    "hallmark-scribble", "shared", "ffmpeg", "bin", "ffmpeg.exe"
)

print("=" * 70)
print("FFmpeg Device Diagnostic")
print("=" * 70)
print(f"\nFFmpeg path: {ffmpeg_path}")
print(f"FFmpeg exists: {os.path.exists(ffmpeg_path)}")
print()

# Run FFmpeg to list devices
print("Running FFmpeg device detection...")
print("=" * 70)

try:
    command = [ffmpeg_path, "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore',
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )
    
    print("\n=== RAW FFMPEG OUTPUT ===")
    print(result.stderr)
    print("\n" + "=" * 70)
    
    # Parse the output
    output = result.stderr
    lines = output.split('\n')
    
    print("\n=== PARSED DEVICES ===\n")
    
    # Video devices
    print("VIDEO DEVICES:")
    in_video_section = False
    video_count = 0
    for line in lines:
        if 'DirectShow video devices' in line:
            in_video_section = True
            continue
        elif 'DirectShow audio devices' in line:
            in_video_section = False
            
        if in_video_section and '"' in line:
            import re
            match = re.search(r'"([^"]+)"', line)
            if match:
                video_count += 1
                print(f"  {video_count}. {match.group(1)}")
    
    if video_count == 0:
        print("  (none found)")
    
    # Audio devices
    print("\nAUDIO DEVICES:")
    in_audio_section = False
    audio_count = 0
    for line in lines:
        if 'DirectShow audio devices' in line:
            in_audio_section = True
            continue
            
        if in_audio_section and '"' in line:
            import re
            match = re.search(r'"([^"]+)"', line)
            if match:
                audio_count += 1
                print(f"  {audio_count}. {match.group(1)}")
    
    if audio_count == 0:
        print("  (none found)")
    
    print("\n" + "=" * 70)
    
    if video_count == 0 and audio_count == 0:
        print("\n⚠️ NO DEVICES DETECTED")
        print("\nPossible reasons:")
        print("1. No cameras/microphones are physically connected")
        print("2. Devices are being used by another application")
        print("3. Device drivers are not installed")
        print("4. Windows privacy settings are blocking access")
        print("\nTo check:")
        print("- Open Windows Settings > Privacy > Camera/Microphone")
        print("- Check if devices appear in Device Manager")
        print("- Try unplugging and reconnecting devices")
        print("- Close other apps that might be using the devices (Zoom, Teams, etc.)")
    
except Exception as e:
    print(f"\n❌ Error running FFmpeg: {e}")
    print("\nMake sure FFmpeg is properly installed.")

print("\n" + "=" * 70)
