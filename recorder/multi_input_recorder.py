"""
Multi-Input Recorder
Records from multiple cameras, microphones, screens, and monitors simultaneously
"""
import subprocess
import os
import logging
import threading
import time
from datetime import datetime
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MultiInputRecorder:
    def __init__(self, output_dir: str = None):
        # Default to user's Downloads folder with Hallmark Record subfolder
        if output_dir is None:
            downloads = os.path.join(os.path.expanduser("~"), "Downloads")
            output_dir = os.path.join(downloads, "Hallmark Record")
        
        self.output_dir = output_dir
        self.recording_processes = []
        self.is_recording = False
        self.ffmpeg_path = self._find_ffmpeg()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"Recordings will be saved to: {output_dir}")
        
    def _find_ffmpeg(self) -> str:
        """Find ffmpeg executable"""
        # Check hallmark-scribble ffmpeg location
        hallmark_ffmpeg = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "hallmark-scribble", "shared", "ffmpeg", "bin", "ffmpeg.exe"
        )
        if os.path.exists(hallmark_ffmpeg):
            return hallmark_ffmpeg
        
        # Check if ffmpeg is in PATH
        import shutil
        ffmpeg_in_path = shutil.which("ffmpeg")
        if ffmpeg_in_path:
            return ffmpeg_in_path
        
        # Return ffmpeg and log warning
        logging.warning("FFmpeg not found. Please install FFmpeg or place it in hallmark-scribble/shared/ffmpeg/bin/")
        return "ffmpeg"  # Will fail but user will see the error
    
    def list_video_devices(self) -> List[str]:
        """List all available video devices (cameras)"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            devices = []
            lines = result.stderr.split('\n')
            
            # FFmpeg outputs devices in format: [dshow @ ...] "Device Name" (video)
            import re
            for line in lines:
                # Look for lines with (video) tag and extract device name
                if '(video)' in line.lower() and '"' in line:
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        device_name = match.group(1)
                        # Filter out alternative names
                        if not device_name.startswith('@device_'):
                            devices.append(device_name)
            
            logging.info(f"Found {len(devices)} video devices: {devices}")
            return devices
        except Exception as e:
            logging.error(f"Error listing video devices: {e}")
            return []
    
    def list_audio_devices(self) -> List[str]:
        """List all available audio devices (microphones)"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            devices = []
            lines = result.stderr.split('\n')
            
            # FFmpeg outputs devices in format: [dshow @ ...] "Device Name" (audio)
            import re
            for line in lines:
                # Look for lines with (audio) tag and extract device name
                if '(audio)' in line.lower() and '"' in line:
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        device_name = match.group(1)
                        # Filter out alternative names
                        if not device_name.startswith('@device_'):
                            devices.append(device_name)
            
            logging.info(f"Found {len(devices)} audio devices: {devices}")
            return devices
        except Exception as e:
            logging.error(f"Error listing audio devices: {e}")
            return []
    
    def list_monitors(self) -> List[Dict]:
        """List all available monitors"""
        try:
            import win32api
            import win32con
            
            monitors = []
            
            def enum_callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
                info = win32api.GetMonitorInfo(hMonitor)
                rect = info['Monitor']
                monitors.append({
                    'name': info.get('Device', f'Monitor {len(monitors) + 1}'),
                    'x': rect[0],
                    'y': rect[1],
                    'width': rect[2] - rect[0],
                    'height': rect[3] - rect[1],
                    'is_primary': info['Flags'] & win32con.MONITORINFOF_PRIMARY
                })
                return True
            
            # Fix: EnumDisplayMonitors takes 2 arguments, not 4
            win32api.EnumDisplayMonitors(None, None)
            
            # If no monitors found via EnumDisplayMonitors, try alternate method
            if not monitors:
                from ctypes import windll, Structure, c_long, POINTER, WINFUNCTYPE, byref
                from ctypes.wintypes import BOOL, HMONITOR, HDC, RECT, LPARAM
                
                class MONITORINFO(Structure):
                    _fields_ = [
                        ('cbSize', c_long),
                        ('rcMonitor', RECT),
                        ('rcWork', RECT),
                        ('dwFlags', c_long)
                    ]
                
                MonitorEnumProc = WINFUNCTYPE(BOOL, HMONITOR, HDC, POINTER(RECT), LPARAM)
                
                def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
                    info = MONITORINFO()
                    info.cbSize = 40
                    windll.user32.GetMonitorInfoW(hMonitor, byref(info))
                    monitors.append({
                        'name': f'Monitor {len(monitors) + 1}',
                        'x': info.rcMonitor.left,
                        'y': info.rcMonitor.top,
                        'width': info.rcMonitor.right - info.rcMonitor.left,
                        'height': info.rcMonitor.bottom - info.rcMonitor.top,
                        'is_primary': info.dwFlags & 1
                    })
                    return True
                
                windll.user32.EnumDisplayMonitors(None, None, MonitorEnumProc(callback), 0)
            
            logging.info(f"Found {len(monitors)} monitors: {monitors}")
            return monitors if monitors else [{'name': 'Primary Monitor', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080, 'is_primary': True}]
        except ImportError:
            logging.warning("pywin32 not installed, using default monitor")
            return [{'name': 'Primary Monitor', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080, 'is_primary': True}]
        except Exception as e:
            logging.error(f"Error listing monitors: {e}")
            return [{'name': 'Primary Monitor', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080, 'is_primary': True}]
    
    def start_camera_recording(self, device_name: str, output_file: str) -> Optional[subprocess.Popen]:
        """Start recording from a camera"""
        try:
            # Don't specify video_size - let FFmpeg use the camera's native resolution
            # This makes it work with any camera regardless of supported resolutions
            command = [
                self.ffmpeg_path, "-y", "-f", "dshow",
                "-framerate", "30",
                "-i", f"video={device_name}",
                "-pix_fmt", "yuv420p",
                output_file
            ]
            
            logging.info(f"Starting camera recording: {device_name} -> {output_file}")
            logging.info(f"Command: {' '.join(command)}")
            logging.info(f"Using camera's native resolution")
            
            # Create log file for this recording
            log_file = output_file.replace('.mp4', '_ffmpeg.log')
            
            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=log,
                    stderr=log,
                    bufsize=0,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            
            logging.info(f"Camera recording started (PID: {process.pid})")
            return process
        except Exception as e:
            logging.error(f"Failed to start camera recording: {e}", exc_info=True)
            return None
    
    def start_microphone_recording(self, device_name: str, output_file: str) -> Optional[subprocess.Popen]:
        """Start recording from a microphone"""
        try:
            command = [
                self.ffmpeg_path, "-y", "-f", "dshow",
                "-i", f"audio={device_name}",
                output_file
            ]
            
            logging.info(f"Starting microphone recording: {device_name} -> {output_file}")
            logging.info(f"Command: {' '.join(command)}")
            
            # Create log file for this recording
            log_file = output_file.replace('.wav', '_ffmpeg.log')
            
            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=log,
                    stderr=log,
                    bufsize=0,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            
            logging.info(f"Microphone recording started (PID: {process.pid})")
            return process
        except Exception as e:
            logging.error(f"Failed to start microphone recording: {e}", exc_info=True)
            return None
    
    def start_monitor_recording(self, monitor: Dict, output_file: str) -> Optional[subprocess.Popen]:
        """Start recording from a monitor/screen"""
        try:
            x, y = monitor['x'], monitor['y']
            w, h = monitor['width'], monitor['height']
            
            # Ensure dimensions are even (required for H.264)
            if w % 2 != 0:
                w -= 1
            if h % 2 != 0:
                h -= 1
            
            command = [
                self.ffmpeg_path, "-y", "-f", "gdigrab",
                "-framerate", "30",
                "-draw_mouse", "1",
                "-offset_x", str(x),
                "-offset_y", str(y),
                "-video_size", f"{w}x{h}",
                "-i", "desktop",
                "-pix_fmt", "yuv420p",
                output_file
            ]
            
            logging.info(f"Starting monitor recording: {monitor['name']} -> {output_file}")
            logging.info(f"Command: {' '.join(command)}")
            
            # Create log file for this recording
            log_file = output_file.replace('.mp4', '_ffmpeg.log')
            
            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=log,
                    stderr=log,
                    bufsize=0,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            
            logging.info(f"Monitor recording started (PID: {process.pid})")
            return process
        except Exception as e:
            logging.error(f"Failed to start monitor recording: {e}", exc_info=True)
            return None
    
    def start_recording(self, 
                       cameras: List[str] = None, 
                       microphones: List[str] = None, 
                       monitors: List[Dict] = None) -> str:
        """
        Start recording from multiple inputs simultaneously
        
        Args:
            cameras: List of camera device names
            microphones: List of microphone device names
            monitors: List of monitor dictionaries
            
        Returns:
            Path to the recording session directory
        """
        if self.is_recording:
            logging.warning("Already recording!")
            return None
        
        # Create session directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(self.output_dir, f"session_{timestamp}")
        os.makedirs(session_dir, exist_ok=True)
        
        logging.info(f"Starting multi-input recording session: {session_dir}")
        
        # Start camera recordings
        if cameras:
            for idx, camera in enumerate(cameras):
                output = os.path.join(session_dir, f"camera_{idx+1}_{camera.replace(' ', '_')}.mp4")
                process = self.start_camera_recording(camera, output)
                if process:
                    self.recording_processes.append({
                        'type': 'camera',
                        'name': camera,
                        'process': process,
                        'output': output
                    })
        
        # Start microphone recordings
        if microphones:
            for idx, mic in enumerate(microphones):
                output = os.path.join(session_dir, f"mic_{idx+1}_{mic.replace(' ', '_')}.wav")
                process = self.start_microphone_recording(mic, output)
                if process:
                    self.recording_processes.append({
                        'type': 'microphone',
                        'name': mic,
                        'process': process,
                        'output': output
                    })
        
        # Start monitor recordings
        if monitors:
            for idx, monitor in enumerate(monitors):
                output = os.path.join(session_dir, f"monitor_{idx+1}_{monitor['name'].replace(' ', '_')}.mp4")
                process = self.start_monitor_recording(monitor, output)
                if process:
                    self.recording_processes.append({
                        'type': 'monitor',
                        'name': monitor['name'],
                        'process': process,
                        'output': output
                    })
        
        self.is_recording = True
        logging.info(f"Recording started with {len(self.recording_processes)} inputs")
        
        return session_dir
    
    def stop_recording(self):
        """Stop all recording processes"""
        if not self.is_recording:
            logging.warning("Not currently recording!")
            return
        
        logging.info("Stopping all recordings...")
        
        for recording in self.recording_processes:
            try:
                process = recording['process']
                logging.info(f"Stopping {recording['type']}: {recording['name']}")
                
                # Send 'q' to gracefully stop ffmpeg
                try:
                    if process.stdin and not process.stdin.closed:
                        process.stdin.write(b'q')
                        process.stdin.flush()
                        process.stdin.close()
                    
                    # Wait for process to finish
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logging.warning(f"Process didn't stop gracefully, terminating...")
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        logging.warning(f"Force killing process...")
                        process.kill()
                        process.wait()
                
                # Check file size
                if os.path.exists(recording['output']):
                    size = os.path.getsize(recording['output'])
                    logging.info(f"Saved: {recording['output']} ({size:,} bytes)")
                else:
                    logging.error(f"Output file not created: {recording['output']}")
                
            except Exception as e:
                logging.error(f"Error stopping {recording['type']}: {e}", exc_info=True)
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except:
                    process.kill()
        
        self.recording_processes.clear()
        self.is_recording = False
        logging.info("All recordings stopped")
    
    def get_recording_status(self) -> Dict:
        """Get current recording status"""
        return {
            'is_recording': self.is_recording,
            'active_inputs': len(self.recording_processes),
            'inputs': [
                {
                    'type': r['type'],
                    'name': r['name'],
                    'output': r['output']
                }
                for r in self.recording_processes
            ]
        }


if __name__ == "__main__":
    # Example usage
    recorder = MultiInputRecorder()
    
    print("\n=== Available Devices ===")
    cameras = recorder.list_video_devices()
    print(f"\nCameras ({len(cameras)}):")
    for i, cam in enumerate(cameras):
        print(f"  {i+1}. {cam}")
    
    microphones = recorder.list_audio_devices()
    print(f"\nMicrophones ({len(microphones)}):")
    for i, mic in enumerate(microphones):
        print(f"  {i+1}. {mic}")
    
    monitors = recorder.list_monitors()
    print(f"\nMonitors ({len(monitors)}):")
    for i, mon in enumerate(monitors):
        print(f"  {i+1}. {mon['name']} - {mon['width']}x{mon['height']} at ({mon['x']}, {mon['y']})")
    
    print("\n=== Test Recording (5 seconds) ===")
    print("Recording from first available devices...")
    
    # Start recording
    session = recorder.start_recording(
        cameras=cameras[:1] if cameras else None,
        microphones=microphones[:1] if microphones else None,
        monitors=monitors[:1] if monitors else None
    )
    
    if session:
        time.sleep(5)
        recorder.stop_recording()
        print(f"\nRecording saved to: {session}")
