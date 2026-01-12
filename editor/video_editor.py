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
    """Export project from timeline with text overlays and transitions"""
    try:
        data = request.json
        session = data['session']
        timeline = data['timeline']
        
        session_path = os.path.join(OUTPUTS_DIR, session)
        output_name = f"timeline_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        output_path = os.path.join(session_path, output_name)
        
        # Collect all video clips from tracks
        all_clips = []
        for track_name, clips in timeline['tracks'].items():
            for clip in clips:
                clip_path = os.path.join(session_path, clip['file'])
                if os.path.exists(clip_path) and clip_path.endswith('.mp4'):
                    all_clips.append({
                        'path': clip_path,
                        'file': clip['file'],
                        'trim_start': clip.get('trim_start', 0),
                        'trim_end': clip.get('trim_end')
                    })
        
        if not all_clips:
            return jsonify({'success': False, 'error': 'No video clips in timeline'}), 400
        
        # Check for text overlays and transitions
        text_overlays = [item for item in timeline.get('items', []) if item.get('type') == 'text']
        transitions = [item for item in timeline.get('items', []) if item.get('type') == 'transition']
        background_music = next((item for item in timeline.get('items', []) if item.get('type') == 'background_music'), None)
        
        # Process videos with trimming if needed
        processed_clips = []
        temp_files = []
        
        for i, clip in enumerate(all_clips):
            if clip['trim_start'] > 0 or clip['trim_end']:
                # Need to trim this clip first
                temp_output = os.path.join(session_path, f'temp_trim_{i}.mp4')
                trim_cmd = [FFMPEG_PATH, '-y', '-i', clip['path']]
                
                if clip['trim_start'] > 0:
                    trim_cmd.extend(['-ss', str(clip['trim_start'])])
                
                if clip['trim_end']:
                    duration = clip['trim_end'] - clip['trim_start']
                    trim_cmd.extend(['-t', str(duration)])
                
                trim_cmd.extend(['-c', 'copy', temp_output])
                
                result = subprocess.run(
                    trim_cmd,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                if result.returncode == 0:
                    processed_clips.append(temp_output)
                    temp_files.append(temp_output)
                else:
                    # If trim fails, use original
                    processed_clips.append(clip['path'])
            else:
                processed_clips.append(clip['path'])
        
        # Build filter complex for text overlays and transitions
        filter_parts = []
        current_input = 0
        
        # If we have transitions, build xfade filters
        if transitions and len(processed_clips) > 1:
            # Sort transitions by position
            transitions_sorted = sorted(transitions, key=lambda x: x.get('afterClip', 0))
            
            # Build xfade chain
            prev_output = f'[{current_input}:v]'
            for trans_idx, transition in enumerate(transitions_sorted):
                next_idx = current_input + 1
                if next_idx < len(processed_clips):
                    trans_type = transition.get('transitionType', 'fade')
                    trans_duration = transition.get('duration', 1)
                    
                    # Map transition types to ffmpeg xfade types
                    xfade_type = {
                        'fade': 'fade',
                        'dissolve': 'dissolve',
                        'wipe': 'wipeleft'
                    }.get(trans_type, 'fade')
                    
                    output_label = f'[v{trans_idx}]' if trans_idx < len(transitions_sorted) - 1 else '[vout]'
                    filter_parts.append(f'{prev_output}[{next_idx}:v]xfade=transition={xfade_type}:duration={trans_duration}:offset=0{output_label}')
                    prev_output = output_label
                    current_input = next_idx
        
        # Add text overlays
        if text_overlays:
            base_input = '[vout]' if transitions else '[0:v]'
            for text_idx, text_item in enumerate(text_overlays):
                text = text_item.get('text', '').replace("'", "\\'")
                font_size = text_item.get('fontSize', 48)
                font_color = text_item.get('fontColor', 'white')
                bg_color = text_item.get('backgroundColor', 'black@0.5')
                position_x = text_item.get('position', {}).get('x', 50)
                position_y = text_item.get('position', {}).get('y', 50)
                start_time = text_item.get('start', 0)
                duration = text_item.get('duration', 5)
                
                # Convert percentage to pixel coordinates
                x_expr = f'(w-text_w)*{position_x/100}'
                y_expr = f'(h-text_h)*{position_y/100}'
                
                output_label = f'[tout{text_idx}]' if text_idx < len(text_overlays) - 1 else '[final]'
                
                filter_parts.append(
                    f"{base_input}drawtext=text='{text}':fontsize={font_size}:fontcolor={font_color}:"
                    f"box=1:boxcolor={bg_color}:x={x_expr}:y={y_expr}:"
                    f"enable='between(t,{start_time},{start_time + duration})'{output_label}"
                )
                base_input = output_label
        
        # Create concat file or use filter complex
        if not filter_parts and not background_music:
            # Simple concatenation without effects
            concat_file = os.path.join(session_path, 'timeline_concat.txt')
            with open(concat_file, 'w') as f:
                for clip_path in processed_clips:
                    f.write(f"file '{os.path.basename(clip_path)}'\n")
            
            command = [
                FFMPEG_PATH, '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                output_path
            ]
        else:
            # Complex filtering with transitions/text/music
            command = [FFMPEG_PATH, '-y']
            
            # Add all input files
            for clip_path in processed_clips:
                command.extend(['-i', clip_path])
            
            # Add background music as input if specified
            music_input_index = None
            if background_music:
                music_path = os.path.join(session_path, background_music['file'])
                if os.path.exists(music_path):
                    command.extend(['-i', music_path])
                    music_input_index = len(processed_clips)
            
            # Build filter complex
            filter_list = filter_parts.copy() if filter_parts else []
            
            # Add audio mixing if background music is present
            if music_input_index is not None:
                volume = background_music.get('volume', 0.3)
                should_loop = background_music.get('loop', False)
                
                # Get video output label
                video_output = '[final]' if text_overlays else ('[vout]' if transitions else '[0:v]')
                
                # Mix original audio with background music
                # [0:a] is from first video, [music_input:a] is background music
                if should_loop:
                    # Loop the music and mix with original audio
                    filter_list.append(
                        f'[{music_input_index}:a]aloop=loop=-1:size=2e+09[music];'
                        f'[0:a][music]amix=inputs=2:weights=1 {volume}[aout]'
                    )
                else:
                    # Mix without looping
                    filter_list.append(
                        f'[0:a][{music_input_index}:a]amix=inputs=2:weights=1 {volume}[aout]'
                    )
            
            # Join all filters
            if filter_list:
                filter_complex = ';'.join(filter_list)
                command.extend(['-filter_complex', filter_complex])
            
            # Map the outputs
            final_video_label = '[final]' if text_overlays else ('[vout]' if transitions else '[0:v]')
            command.extend(['-map', final_video_label])
            
            # Map audio output
            if music_input_index is not None:
                command.extend(['-map', '[aout]'])
            else:
                # Use original audio
                command.extend(['-map', '0:a?'])
            
            # Encoding settings
            command.extend([
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-shortest',  # Stop when shortest stream ends
                output_path
            ])
        
        logging.info(f"Exporting timeline: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # Clean up temp files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        
        concat_file = os.path.join(session_path, 'timeline_concat.txt')
        if os.path.exists(concat_file):
            try:
                os.remove(concat_file)
            except:
                pass
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'output': output_name,
                'message': 'Timeline exported successfully with effects'
            })
        else:
            logging.error(f"FFmpeg error: {result.stderr}")
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
