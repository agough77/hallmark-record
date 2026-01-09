"""
Multi-Input Video Editor
Simple interface for editing recordings from multiple sources
"""
import os
import sys
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
import subprocess
import logging
from datetime import datetime

# Determine template folder location (works for both script and PyInstaller bundle)
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle - templates are in _MEIPASS
    template_folder = os.path.join(sys._MEIPASS, 'templates')
else:
    # Running as script - templates are in editor/templates
    template_folder = os.path.join(os.path.dirname(__file__), 'templates')

app = Flask(__name__, template_folder=template_folder)
logging.basicConfig(level=logging.INFO)

# Configuration - Save to user's Downloads folder
downloads = os.path.join(os.path.expanduser("~"), "Downloads")
OUTPUTS_DIR = os.path.join(downloads, "Hallmark Record")
FFMPEG_PATH = "ffmpeg"  # Will be resolved

def find_ffmpeg():
    """Find ffmpeg executable"""
    # Determine the base path (works for both script and PyInstaller bundle)
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running as script
        base_path = os.path.dirname(os.path.dirname(__file__))
    
    # Check bundled ffmpeg location (PyInstaller)
    bundled_ffmpeg = os.path.join(base_path, "ffmpeg", "bin", "ffmpeg.exe")
    if os.path.exists(bundled_ffmpeg):
        return bundled_ffmpeg
    
    # Check hallmark-scribble ffmpeg location (development)
    hallmark_ffmpeg = os.path.join(
        base_path,
        "hallmark-scribble", "shared", "ffmpeg", "bin", "ffmpeg.exe"
    )
    if os.path.exists(hallmark_ffmpeg):
        return hallmark_ffmpeg
    
    return "ffmpeg"

FFMPEG_PATH = find_ffmpeg()

@app.route('/')
def index():
    """Main editor interface - redirect to timeline editor"""
    return render_template('timeline_editor.html')

@app.route('/api/sessions')
def list_sessions():
    """List all recording sessions"""
    try:
        sessions = []
        if os.path.exists(OUTPUTS_DIR):
            for session_name in os.listdir(OUTPUTS_DIR):
                session_path = os.path.join(OUTPUTS_DIR, session_name)
                if os.path.isdir(session_path):
                    # Get all video and audio files
                    files = []
                    for file in os.listdir(session_path):
                        if file.endswith(('.mp4', '.wav', '.mp3')):
                            file_path = os.path.join(session_path, file)
                            file_info = {
                                'name': file,
                                'type': 'video' if file.endswith('.mp4') else 'audio',
                                'size': os.path.getsize(file_path),
                                'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                            }
                            files.append(file_info)
                    
                    sessions.append({
                        'name': session_name,
                        'path': session_path,
                        'files': files,
                        'file_count': len(files)
                    })
        
        return jsonify({'sessions': sessions})
    except Exception as e:
        logging.error(f"Error listing sessions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/preview/<path:session_name>/<path:filename>')
def preview_file(session_name, filename):
    """Preview a video or audio file"""
    try:
        session_path = os.path.join(OUTPUTS_DIR, session_name)
        return send_from_directory(session_path, filename)
    except Exception as e:
        logging.error(f"Error previewing file: {e}")
        return jsonify({'error': str(e)}), 404

@app.route('/api/trim', methods=['POST'])
def trim_video():
    """Trim a video file"""
    try:
        data = request.json
        session = data['session']
        filename = data['filename']
        start_time = data['start_time']
        end_time = data['end_time']
        
        input_path = os.path.join(OUTPUTS_DIR, session, filename)
        output_filename = f"trimmed_{filename}"
        output_path = os.path.join(OUTPUTS_DIR, session, output_filename)
        
        duration = end_time - start_time
        
        command = [
            FFMPEG_PATH, '-y',
            '-ss', str(start_time),
            '-t', str(duration),
            '-i', input_path,
            '-c', 'copy',
            output_path
        ]
        
        logging.info(f"Trimming video: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'output': output_filename,
                'message': f'Video trimmed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr
            }), 500
            
    except Exception as e:
        logging.error(f"Error trimming video: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/merge', methods=['POST'])
def merge_videos():
    """Merge multiple video/audio files"""
    try:
        data = request.json
        session = data['session']
        files = data['files']  # List of filenames to merge
        output_name = data.get('output_name', 'merged_output.mp4')
        layout = data.get('layout', 'grid')  # grid, horizontal, vertical
        
        session_path = os.path.join(OUTPUTS_DIR, session)
        output_path = os.path.join(session_path, output_name)
        
        # Create filter complex for layout
        if layout == 'grid' and len(files) > 1:
            # Grid layout (2x2, 3x3, etc.)
            if len(files) == 2:
                filter_complex = "[0:v][1:v]hstack=inputs=2[v]"
                map_args = ["-map", "[v]"]
            elif len(files) == 3:
                filter_complex = "[0:v][1:v][2:v]hstack=inputs=3[v]"
                map_args = ["-map", "[v]"]
            elif len(files) == 4:
                filter_complex = "[0:v][1:v]hstack=inputs=2[top];[2:v][3:v]hstack=inputs=2[bottom];[top][bottom]vstack=inputs=2[v]"
                map_args = ["-map", "[v]"]
            else:
                # For more than 4, use simple concatenation
                filter_complex = None
                map_args = []
        elif layout == 'horizontal':
            filter_complex = f"{''.join([f'[{i}:v]' for i in range(len(files))])}hstack=inputs={len(files)}[v]"
            map_args = ["-map", "[v]"]
        elif layout == 'vertical':
            filter_complex = f"{''.join([f'[{i}:v]' for i in range(len(files))])}vstack=inputs={len(files)}[v]"
            map_args = ["-map", "[v]"]
        else:
            # Concatenate
            filter_complex = None
            map_args = []
        
        # Build ffmpeg command
        command = [FFMPEG_PATH, '-y']
        
        # Add input files
        for file in files:
            command.extend(['-i', os.path.join(session_path, file)])
        
        # Add filter if applicable
        if filter_complex:
            command.extend(['-filter_complex', filter_complex])
            command.extend(map_args)
        else:
            # Simple concatenation
            concat_file = os.path.join(session_path, 'concat_list.txt')
            with open(concat_file, 'w') as f:
                for file in files:
                    f.write(f"file '{file}'\n")
            command = [FFMPEG_PATH, '-y', '-f', 'concat', '-safe', '0', '-i', concat_file]
        
        command.extend(['-c:v', 'libx264', '-preset', 'fast', output_path])
        
        logging.info(f"Merging videos: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'output': output_name,
                'message': f'Videos merged successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr
            }), 500
            
    except Exception as e:
        logging.error(f"Error merging videos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-audio', methods=['POST'])
def add_audio_to_video():
    """Add audio track to video"""
    try:
        data = request.json
        session = data['session']
        video_file = data['video_file']
        audio_file = data['audio_file']
        output_name = data.get('output_name', 'video_with_audio.mp4')
        
        session_path = os.path.join(OUTPUTS_DIR, session)
        video_path = os.path.join(session_path, video_file)
        audio_path = os.path.join(session_path, audio_file)
        output_path = os.path.join(session_path, output_name)
        
        command = [
            FFMPEG_PATH, '-y',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0',
            output_path
        ]
        
        logging.info(f"Adding audio to video: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'output': output_name,
                'message': 'Audio added successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr
            }), 500
            
    except Exception as e:
        logging.error(f"Error adding audio: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export', methods=['POST'])
def export_final():
    """Export final edited video"""
    try:
        data = request.json
        session = data['session']
        input_file = data['input_file']
        export_format = data.get('format', 'mp4')
        quality = data.get('quality', 'high')
        
        session_path = os.path.join(OUTPUTS_DIR, session)
        input_path = os.path.join(session_path, input_file)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"export_{timestamp}.{export_format}"
        output_path = os.path.join(session_path, output_filename)
        
        # Quality presets
        quality_settings = {
            'high': ['-crf', '18', '-preset', 'slow'],
            'medium': ['-crf', '23', '-preset', 'medium'],
            'low': ['-crf', '28', '-preset', 'fast']
        }
        
        command = [
            FFMPEG_PATH, '-y',
            '-i', input_path,
            '-c:v', 'libx264',
            *quality_settings.get(quality, quality_settings['medium']),
            '-c:a', 'aac',
            '-b:a', '192k',
            output_path
        ]
        
        logging.info(f"Exporting video: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'output': output_filename,
                'message': 'Video exported successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr
            }), 500
            
    except Exception as e:
        logging.error(f"Error exporting video: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/timeline')
def timeline_editor():
    """Timeline-based editor (Clipchamp style)"""
    return render_template('timeline_editor.html')

@app.route('/api/export-timeline', methods=['POST'])
def export_timeline():
    """Export project from timeline"""
    try:
        data = request.json
        session = data['session']
        timeline = data['timeline']
        
        # For now, just merge all clips in order
        # In future, this would handle multi-track composition
        session_path = os.path.join(OUTPUTS_DIR, session)
        output_name = f"timeline_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        output_path = os.path.join(session_path, output_name)
        
        # Collect all video clips from tracks
        all_clips = []
        for track_name, clips in timeline['tracks'].items():
            for clip in clips:
                clip_path = os.path.join(session_path, clip['file'])
                if os.path.exists(clip_path) and clip_path.endswith('.mp4'):
                    all_clips.append(clip_path)
        
        if not all_clips:
            return jsonify({'success': False, 'error': 'No video clips in timeline'}), 400
        
        # Create concat file
        concat_file = os.path.join(session_path, 'timeline_concat.txt')
        with open(concat_file, 'w') as f:
            for clip_path in all_clips:
                f.write(f"file '{os.path.basename(clip_path)}'\n")
        
        # Concatenate videos
        command = [
            FFMPEG_PATH, '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            output_path
        ]
        
        logging.info(f"Exporting timeline: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # Clean up
        if os.path.exists(concat_file):
            os.remove(concat_file)
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'output': output_name,
                'message': 'Timeline exported successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr
            }), 500
            
    except Exception as e:
        logging.error(f"Error exporting timeline: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/overlay', methods=['POST'])
def overlay_videos():
    """Overlay one video on top of another (picture-in-picture)"""
    try:
        data = request.json
        session = data['session']
        background_video = data['background_video']  # Desktop recording
        overlay_video = data['overlay_video']  # Camera recording
        output_name = data.get('output_name', 'overlay_output.mp4')
        
        # Position and size of overlay
        position_x = data.get('position_x', '20')
        position_y = data.get('position_y', '20')
        
        # Use exact pixel dimensions if provided, otherwise use scale
        overlay_width = data.get('overlay_width')
        overlay_height = data.get('overlay_height')
        overlay_scale = data.get('overlay_scale', 0.25)
        
        session_path = os.path.join(OUTPUTS_DIR, session)
        background_path = os.path.join(session_path, background_video)
        overlay_path = os.path.join(session_path, overlay_video)
        output_path = os.path.join(session_path, output_name)
        
        # Build filter complex for picture-in-picture
        if overlay_width and overlay_height:
            # Scale overlay to exact pixel dimensions
            filter_complex = f"[1:v]scale={overlay_width}:{overlay_height}[ovrl];[0:v][ovrl]overlay={position_x}:{position_y}"
        else:
            # Scale overlay by percentage of its original size
            filter_complex = f"[1:v]scale=iw*{overlay_scale}:ih*{overlay_scale}[ovrl];[0:v][ovrl]overlay={position_x}:{position_y}"
        
        command = [
            FFMPEG_PATH, '-y',
            '-i', background_path,  # Input 0: background (desktop)
            '-i', overlay_path,     # Input 1: overlay (camera)
            '-filter_complex', filter_complex,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            output_path
        ]
        
        logging.info(f"Creating overlay: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'output': output_name,
                'message': 'Overlay created successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr
            }), 500
            
    except Exception as e:
        logging.error(f"Error creating overlay: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/record-audio', methods=['POST'])
def record_audio():
    """Record new audio from microphone"""
    try:
        data = request.json
        session = data['session']
        duration = data.get('duration', 10)  # Default 10 seconds
        device_name = data.get('device_name', None)  # Microphone name
        output_name = data.get('output_name', f'recorded_audio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.wav')
        
        session_path = os.path.join(OUTPUTS_DIR, session)
        os.makedirs(session_path, exist_ok=True)
        output_path = os.path.join(session_path, output_name)
        
        # Build command
        if device_name:
            # Use specific microphone
            command = [
                FFMPEG_PATH, '-y',
                '-f', 'dshow',
                '-i', f'audio={device_name}',
                '-t', str(duration),
                output_path
            ]
        else:
            # Use default microphone
            command = [
                FFMPEG_PATH, '-y',
                '-f', 'dshow',
                '-list_devices', 'true',
                '-i', 'dummy'
            ]
            # Get first available audio device
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Parse device name from error output
            import re
            for line in result.stderr.split('\n'):
                if '(audio)' in line.lower():
                    match = re.search(r'"([^"]+)".*\(audio\)', line, re.IGNORECASE)
                    if match:
                        device_name = match.group(1)
                        break
            
            if not device_name:
                return jsonify({'success': False, 'error': 'No audio device found'}), 400
            
            command = [
                FFMPEG_PATH, '-y',
                '-f', 'dshow',
                '-i', f'audio={device_name}',
                '-t', str(duration),
                output_path
            ]
        
        logging.info(f"Recording audio: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            return jsonify({
                'success': True,
                'output': output_name,
                'message': f'Audio recorded successfully ({duration}s)',
                'device': device_name
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr
            }), 500
            
    except Exception as e:
        logging.error(f"Error recording audio: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete-file', methods=['POST'])
def delete_file():
    """Delete a file from a session"""
    try:
        data = request.json
        session = data['session']
        filename = data['filename']
        
        file_path = os.path.join(OUTPUTS_DIR, session, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        os.remove(file_path)
        logging.info(f"Deleted file: {file_path}")
        
        return jsonify({
            'success': True,
            'message': f'File {filename} deleted successfully'
        })
            
    except Exception as e:
        logging.error(f"Error deleting file: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/launch-recorder', methods=['POST'])
def launch_recorder():
    """Launch the main recording application"""
    try:
        main_py = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.py')
        
        if not os.path.exists(main_py):
            return jsonify({'success': False, 'error': 'main.py not found'}), 404
        
        # Launch main.py in a new process
        if os.name == 'nt':  # Windows
            subprocess.Popen(['python', main_py], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:  # Unix/Mac
            subprocess.Popen(['python', main_py])
        
        logging.info("Launched recording application")
        return jsonify({'success': True, 'message': 'Recording app launched'})
        
    except Exception as e:
        logging.error(f"Error launching recorder: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    print("Starting Multi-Input Video Editor...")
    print(f"Outputs directory: {OUTPUTS_DIR}")
    print(f"FFmpeg path: {FFMPEG_PATH}")
    print("\nEditor will be available at: http://localhost:5500")
    app.run(debug=True, port=5500)
