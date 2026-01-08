"""
Test recording with detailed output
"""
import subprocess
import os
import time

ffmpeg_path = os.path.join(
    os.path.dirname(__file__),
    "hallmark-scribble", "shared", "ffmpeg", "bin", "ffmpeg.exe"
)

output_dir = "test_recording"
os.makedirs(output_dir, exist_ok=True)

print("=" * 70)
print("Testing Screen Recording")
print("=" * 70)
print(f"\nFFmpeg: {ffmpeg_path}")
print(f"Output dir: {output_dir}")
print()

# Test 1: Record screen for 5 seconds
print("Test 1: Recording screen for 5 seconds...")
screen_output = os.path.join(output_dir, "screen_test.mp4")

command = [
    ffmpeg_path, "-y",
    "-f", "gdigrab",
    "-framerate", "30",
    "-t", "5",  # Record for 5 seconds
    "-i", "desktop",
    "-pix_fmt", "yuv420p",
    screen_output
]

print(f"Command: {' '.join(command)}")
print("\nRecording...")

result = subprocess.run(command, capture_output=True, text=True)

print(f"\nReturn code: {result.returncode}")
if result.returncode == 0:
    size = os.path.getsize(screen_output)
    print(f"✓ Screen recording successful! File size: {size:,} bytes")
else:
    print(f"✗ Screen recording failed!")
    print("STDERR:", result.stderr[-500:])

print("\n" + "=" * 70)

# Test 2: Record camera for 5 seconds
print("\nTest 2: Recording camera for 5 seconds...")
camera_output = os.path.join(output_dir, "camera_test.mp4")

command = [
    ffmpeg_path, "-y",
    "-f", "dshow",
    "-video_size", "640x480",
    "-framerate", "30",
    "-t", "5",  # Record for 5 seconds
    "-i", "video=720p HD Camera",
    "-pix_fmt", "yuv420p",
    camera_output
]

print(f"Command: {' '.join(command)}")
print("\nRecording...")

result = subprocess.run(command, capture_output=True, text=True)

print(f"\nReturn code: {result.returncode}")
if result.returncode == 0:
    size = os.path.getsize(camera_output)
    print(f"✓ Camera recording successful! File size: {size:,} bytes")
else:
    print(f"✗ Camera recording failed!")
    print("STDERR:", result.stderr[-500:])

print("\n" + "=" * 70)

# Test 3: Record microphone for 5 seconds
print("\nTest 3: Recording microphone for 5 seconds...")
mic_output = os.path.join(output_dir, "mic_test.wav")

command = [
    ffmpeg_path, "-y",
    "-f", "dshow",
    "-t", "5",  # Record for 5 seconds
    "-i", "audio=Microphone Array (Intel® Smart Sound Technology for Digital Microphones)",
    mic_output
]

print(f"Command: {' '.join(command)}")
print("\nRecording...")

result = subprocess.run(command, capture_output=True, text=True)

print(f"\nReturn code: {result.returncode}")
if result.returncode == 0:
    size = os.path.getsize(mic_output)
    print(f"✓ Microphone recording successful! File size: {size:,} bytes")
else:
    print(f"✗ Microphone recording failed!")
    print("STDERR:", result.stderr[-500:])

print("\n" + "=" * 70)
print("\nTest complete! Check the test_recording folder.")
print("=" * 70)
