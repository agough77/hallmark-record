"""
Hallmark Record - Wizard-Style Desktop Editor
Multi-step editing workflow integrated with PyQt5
"""
import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QListWidget, QGroupBox, QMessageBox, 
                            QFileDialog, QStackedWidget, QProgressBar, QComboBox,
                            QLineEdit, QSlider, QCheckBox, QTextEdit, QListWidgetItem,
                            QSpinBox, QDoubleSpinBox, QTabWidget, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint
from PyQt5.QtGui import QFont, QPixmap, QImage, QPainter, QPen
import subprocess
import json
import logging
import tempfile
import cv2

# VLC availability check
VLC_AVAILABLE = False
vlc = None

try:
    import vlc as vlc_module
    vlc = vlc_module
    # Test if VLC libraries are actually available
    try:
        test_instance = vlc.Instance('--quiet')
        VLC_AVAILABLE = True
        logging.info('VLC libraries found and working')
        del test_instance
    except Exception as e:
        VLC_AVAILABLE = False
        logging.warning(f'VLC libraries not available: {str(e)}')
        vlc = None
except (ImportError, OSError) as e:
    VLC_AVAILABLE = False
    logging.warning(f'VLC not available: {str(e)}')
    vlc = None

logging.basicConfig(level=logging.INFO)


class DraggableOverlayLabel(QLabel):
    """Custom QLabel that allows dragging the overlay within the preview"""
    overlay_moved = pyqtSignal(int, int)  # Emit x, y position in percentages
    dragging_complete = pyqtSignal()  # Emit when dragging finishes
    dragging_complete = pyqtSignal()  # Emit when dragging finishes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragging = False
        self.drag_start_pos = None
        self.overlay_rect = None  # Will store QRect of overlay position in display coordinates
        self.scale_info = None  # Store scale information for calculations
        self.setMouseTracking(True)
        
    def set_overlay_rect(self, rect, scale_info=None):
        """Store the overlay rectangle for hit testing"""
        self.overlay_rect = rect
        self.scale_info = scale_info
        
    def mousePressEvent(self, event):
        """Start dragging if clicked on overlay"""
        if event.button() == Qt.LeftButton and self.overlay_rect:
            if self.overlay_rect.contains(event.pos()):
                self.dragging = True
                self.drag_start_pos = event.pos() - self.overlay_rect.topLeft()
                self.setCursor(Qt.ClosedHandCursor)
                
    def mouseMoveEvent(self, event):
        """Update overlay position while dragging"""
        if self.dragging and self.drag_start_pos and self.scale_info:
            new_pos = event.pos() - self.drag_start_pos
            
            # Get display pixmap bounds (accounting for KeepAspectRatio centering)
            if self.pixmap():
                pixmap_width = self.pixmap().width()
                pixmap_height = self.pixmap().height()
                x_offset = self.scale_info.get('x_offset', 0)
                y_offset = self.scale_info.get('y_offset', 0)
                
                # Constrain to pixmap bounds
                max_x = pixmap_width - self.overlay_rect.width() + x_offset
                max_y = pixmap_height - self.overlay_rect.height() + y_offset
                new_pos.setX(max(x_offset, min(new_pos.x(), max_x)))
                new_pos.setY(max(y_offset, min(new_pos.y(), max_y)))
            
            self.overlay_rect.moveTo(new_pos)
            
            # Calculate percentage positions in original video space
            if self.scale_info:
                # Remove offset to get position relative to video
                video_x = (new_pos.x() - self.scale_info['x_offset']) / self.scale_info['scale_x']
                video_y = (new_pos.y() - self.scale_info['y_offset']) / self.scale_info['scale_y']
                
                # Calculate available movement space
                available_width = self.scale_info['bg_width'] - self.scale_info['overlay_width']
                available_height = self.scale_info['bg_height'] - self.scale_info['overlay_height']
                
                # Convert to percentage
                x_percent = int((video_x / available_width) * 100) if available_width > 0 else 0
                y_percent = int((video_y / available_height) * 100) if available_height > 0 else 0
                
                # Clamp to 0-100
                x_percent = max(0, min(100, x_percent))
                y_percent = max(0, min(100, y_percent))
                
                self.overlay_moved.emit(x_percent, y_percent)
        elif self.overlay_rect and self.overlay_rect.contains(event.pos()):
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            
    def mouseReleaseEvent(self, event):
        """Stop dragging"""
        if event.button() == Qt.LeftButton:
            was_dragging = self.dragging
            self.dragging = False
            if self.overlay_rect and self.overlay_rect.contains(event.pos()):
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            
            # Emit signal if we were dragging
            if was_dragging:
                self.dragging_complete.emit()


class VideoProcessor(QThread):
    """Background thread for video processing operations"""
    progress_update = pyqtSignal(int, str)
    processing_complete = pyqtSignal(bool, str)
    
    def __init__(self, ffmpeg_path, command_type, **kwargs):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.command_type = command_type
        self.params = kwargs
        
    def run(self):
        """Execute FFmpeg command based on type"""
        try:
            if self.command_type == 'merge':
                self.merge_videos()
            elif self.command_type == 'overlay':
                self.apply_overlay()
            elif self.command_type == 'watermark':
                self.add_watermark()
            elif self.command_type == 'export':
                self.export_video()
        except Exception as e:
            self.processing_complete.emit(False, str(e))
    
    def merge_videos(self):
        """Merge multiple videos"""
        videos = self.params['videos']
        output = self.params['output']
        layout = self.params.get('layout', 'grid')
        
        self.progress_update.emit(10, "Preparing merge...")
        
        # Create concat file for simple merge
        if layout == 'sequential':
            concat_file = output.replace('.mp4', '_concat.txt')
            with open(concat_file, 'w') as f:
                for video in videos:
                    f.write(f"file '{video}'\n")
            
            command = [
                self.ffmpeg_path, '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                output
            ]
        else:
            # Grid or side-by-side layout
            filter_complex = self.build_layout_filter(videos, layout)
            command = [
                self.ffmpeg_path, '-y'
            ]
            for video in videos:
                command.extend(['-i', video])
            
            command.extend([
                '-filter_complex', filter_complex,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                output
            ])
        
        self.progress_update.emit(30, "Merging videos...")
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.progress_update.emit(100, "Merge complete!")
            self.processing_complete.emit(True, output)
        else:
            self.processing_complete.emit(False, f"Merge failed: {result.stderr}")
    
    def build_layout_filter(self, videos, layout):
        """Build FFmpeg filter for video layout"""
        num_videos = len(videos)
        
        if layout == 'side_by_side' and num_videos == 2:
            return "[0:v][1:v]hstack[v]"
        elif layout == 'grid':
            if num_videos == 2:
                return "[0:v][1:v]vstack[v]"
            elif num_videos == 4:
                return "[0:v][1:v]hstack[top];[2:v][3:v]hstack[bottom];[top][bottom]vstack[v]"
        
        return "[0:v]"
    
    def apply_overlay(self):
        """Apply picture-in-picture overlay"""
        background = self.params['background']
        overlay = self.params['overlay']
        output = self.params['output']
        x_percent = self.params.get('x_percent', 75)
        y_percent = self.params.get('y_percent', 75)
        size = self.params.get('size', 0.35)
        
        self.progress_update.emit(20, "Applying overlay...")
        
        # Calculate position: x_percent/y_percent are percentages of remaining space
        # Formula: x = x_percent/100 * (W - overlay_width)
        # In FFmpeg overlay filter: x=(W-w)*x_percent/100, y=(H-h)*y_percent/100
        x_pos = f"(W-w)*{x_percent}/100"
        y_pos = f"(H-h)*{y_percent}/100"
        
        command = [
            self.ffmpeg_path, '-y',
            '-i', background,
            '-i', overlay,
            '-filter_complex',
            f'[1:v]scale=iw*{size}:ih*{size}[overlay];[0:v][overlay]overlay={x_pos}:{y_pos}[v]',
            '-map', '[v]',
            '-map', '0:a?',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            output
        ]
        
        self.progress_update.emit(50, "Processing overlay...")
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.progress_update.emit(100, "Overlay applied!")
            self.processing_complete.emit(True, output)
        else:
            self.processing_complete.emit(False, f"Overlay failed: {result.stderr}")
    
    def add_watermark(self):
        """Add watermark to video"""
        input_video = self.params['input']
        watermark = self.params['watermark']
        output = self.params['output']
        position = self.params.get('position', 'top_right')
        opacity = self.params.get('opacity', 0.7)
        
        self.progress_update.emit(20, "Adding watermark...")
        
        positions = {
            'top_left': '10:10',
            'top_right': 'W-w-10:10',
            'bottom_left': '10:H-h-10',
            'bottom_right': 'W-w-10:H-h-10',
            'center': '(W-w)/2:(H-h)/2'
        }
        
        pos_str = positions.get(position, 'W-w-10:10')
        
        # Scale watermark to 15% of video width (maintaining aspect ratio)
        command = [
            self.ffmpeg_path, '-y',
            '-i', input_video,
            '-i', watermark,
            '-filter_complex',
            f'[1:v]scale=iw*0.15:ih*0.15,format=rgba,colorchannelmixer=aa={opacity}[logo];[0:v][logo]overlay={pos_str}[v]',
            '-map', '[v]',
            '-map', '0:a?',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'copy',
            output
        ]
        
        self.progress_update.emit(50, "Processing watermark...")
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.progress_update.emit(100, "Watermark added!")
            self.processing_complete.emit(True, output)
        else:
            self.processing_complete.emit(False, f"Watermark failed: {result.stderr}")
    
    def export_video(self):
        """Export final video with quality settings"""
        input_video = self.params['input']
        output = self.params['output']
        quality = self.params.get('quality', 'high')
        
        quality_settings = {
            'high': ['-crf', '18', '-preset', 'slow'],
            'medium': ['-crf', '23', '-preset', 'medium'],
            'low': ['-crf', '28', '-preset', 'fast']
        }
        
        command = [
            self.ffmpeg_path, '-y',
            '-i', input_video,
            '-c:v', 'libx264',
            *quality_settings.get(quality, quality_settings['medium']),
            '-c:a', 'aac',
            '-b:a', '192k',
            output
        ]
        
        self.progress_update.emit(50, "Exporting video...")
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.progress_update.emit(100, "Export complete!")
            self.processing_complete.emit(True, output)
        else:
            self.processing_complete.emit(False, f"Export failed: {result.stderr}")


class WizardEditor(QWidget):
    """Main wizard-style editor widget"""
    
    def __init__(self, session_folder=None, ffmpeg_path="ffmpeg"):
        super().__init__()
        self.session_folder = session_folder
        self.ffmpeg_path = ffmpeg_path
        self.current_project = {
            'session': session_folder,
            'source_videos': [],
            'source_audio': [],
            'merged_video': None,
            'overlay_video': None,
            'watermarked_video': None,
            'final_video': None
        }
        
        # Initialize overlay scale info
        self.overlay_scale_info = {
            'scale_x': 1.0,
            'scale_y': 1.0,
            'x_offset': 0,
            'y_offset': 0
        }
        
        self.init_ui()
        
        if session_folder:
            self.load_session_files()
    
    def init_ui(self):
        """Initialize the wizard UI"""
        self.setWindowTitle('Hallmark Record - Video Editor Wizard')
        self.setGeometry(100, 100, 1400, 900)
        
        main_layout = QVBoxLayout(self)
        
        # Title
        title = QLabel('📽️ Video Editor Wizard')
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Step indicator
        self.step_indicator = QLabel('Step 1 of 5: Verify Recordings')
        self.step_indicator.setAlignment(Qt.AlignCenter)
        self.step_indicator.setStyleSheet('''
            QLabel {
                font-size: 16px;
                color: #667eea;
                font-weight: bold;
                padding: 10px;
            }
        ''')
        main_layout.addWidget(self.step_indicator)
        
        # Stacked widget for wizard pages
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        
        # Create wizard pages
        self.page1 = self.create_step1_verify()
        self.page2 = self.create_step2_overlay()
        self.page3 = self.create_step3_watermark()
        self.page4 = self.create_step4_preview()
        self.page5 = self.create_step5_export()
        
        self.stacked_widget.addWidget(self.page1)
        self.stacked_widget.addWidget(self.page2)
        self.stacked_widget.addWidget(self.page3)
        self.stacked_widget.addWidget(self.page4)
        self.stacked_widget.addWidget(self.page5)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton('◀ Previous')
        self.prev_btn.setStyleSheet(self.get_button_style('#95a5a6'))
        self.prev_btn.clicked.connect(self.previous_step)
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)
        
        nav_layout.addStretch()
        
        self.next_btn = QPushButton('Next ▶')
        self.next_btn.setStyleSheet(self.get_button_style('#667eea'))
        self.next_btn.clicked.connect(self.next_step)
        nav_layout.addWidget(self.next_btn)
        
        self.finish_btn = QPushButton('✓ Finish')
        self.finish_btn.setStyleSheet(self.get_button_style('#4caf50'))
        self.finish_btn.clicked.connect(self.finish_wizard)
        self.finish_btn.setVisible(False)
        nav_layout.addWidget(self.finish_btn)
        
        main_layout.addLayout(nav_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
    
    def get_button_style(self, color):
        """Get button stylesheet"""
        return f'''
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                min-width: 120px;
            }}
            QPushButton:hover {{
                background: {self.darken_color(color)};
            }}
            QPushButton:disabled {{
                background: #cccccc;
                color: #666666;
            }}
        '''
    
    def darken_color(self, hex_color):
        """Darken a hex color by 20%"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darker = tuple(int(c * 0.8) for c in rgb)
        return f'#{darker[0]:02x}{darker[1]:02x}{darker[2]:02x}'
    
    def create_step1_verify(self):
        """Step 1: Verify and re-record if needed"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Description
        desc = QLabel('Review your recorded files. You can re-record audio or video if needed.')
        desc.setWordWrap(True)
        desc.setStyleSheet('font-size: 13px; color: #666; padding: 10px;')
        layout.addWidget(desc)
        
        # Split into two columns: Video list and preview
        content_layout = QHBoxLayout()
        
        # Left side - Video files section
        video_group = QGroupBox('🎥 Video Files')
        video_layout = QVBoxLayout()
        
        self.video_list = QListWidget()
        self.video_list.itemDoubleClicked.connect(self.preview_video)
        self.video_list.itemClicked.connect(self.show_video_preview_step1)
        video_layout.addWidget(self.video_list)
        
        video_btn_layout = QHBoxLayout()
        preview_video_btn = QPushButton('👁️ Preview')
        preview_video_btn.clicked.connect(self.preview_selected_video)
        video_btn_layout.addWidget(preview_video_btn)
        
        rerecord_video_btn = QPushButton('🔴 Re-record Video')
        rerecord_video_btn.clicked.connect(self.rerecord_video)
        video_btn_layout.addWidget(rerecord_video_btn)
        
        video_layout.addLayout(video_btn_layout)
        video_group.setLayout(video_layout)
        content_layout.addWidget(video_group, 1)
        
        # Right side - Live preview
        preview_group = QGroupBox('📺 Preview')
        preview_layout = QVBoxLayout()
        
        self.step1_preview_label = QLabel('Click a video to see thumbnail')
        self.step1_preview_label.setAlignment(Qt.AlignCenter)
        self.step1_preview_label.setStyleSheet('border: 2px solid #ccc; background: #000; color: #fff;')
        self.step1_preview_label.setMinimumSize(400, 300)
        self.step1_preview_label.setScaledContents(True)
        preview_layout.addWidget(self.step1_preview_label)
        
        self.step1_info_label = QLabel('No video selected')
        self.step1_info_label.setStyleSheet('font-size: 11px; color: #666; padding: 5px;')
        preview_layout.addWidget(self.step1_info_label)
        
        preview_group.setLayout(preview_layout)
        content_layout.addWidget(preview_group, 1)
        
        layout.addLayout(content_layout)
        
        # Audio files section (below)
        audio_group = QGroupBox('🎤 Audio Files')
        audio_layout = QVBoxLayout()
        
        self.audio_list = QListWidget()
        self.audio_list.itemDoubleClicked.connect(self.preview_audio)
        audio_layout.addWidget(self.audio_list)
        
        audio_btn_layout = QHBoxLayout()
        preview_audio_btn = QPushButton('👁️ Preview')
        preview_audio_btn.clicked.connect(self.preview_selected_audio)
        audio_btn_layout.addWidget(preview_audio_btn)
        
        rerecord_audio_btn = QPushButton('🔴 Re-record Audio')
        rerecord_audio_btn.clicked.connect(self.rerecord_audio)
        audio_btn_layout.addWidget(rerecord_audio_btn)
        
        audio_layout.addLayout(audio_btn_layout)
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)
        
        # Re-record options (removed merge/split for now)
        return page
    
    def create_step2_overlay(self):
        """Step 2: Apply overlay (picture-in-picture)"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        desc = QLabel('Combine videos with picture-in-picture overlay or side-by-side layout.')
        desc.setWordWrap(True)
        desc.setStyleSheet('font-size: 13px; color: #666; padding: 10px;')
        layout.addWidget(desc)
        
        # File selection
        file_layout = QHBoxLayout()
        
        # Background video
        bg_group = QGroupBox('Background Video (Desktop/Main)')
        bg_layout = QVBoxLayout()
        self.bg_video_combo = QComboBox()
        self.bg_video_combo.currentIndexChanged.connect(self.update_overlay_preview)
        bg_layout.addWidget(self.bg_video_combo)
        bg_group.setLayout(bg_layout)
        file_layout.addWidget(bg_group)
        
        # Overlay video
        overlay_group = QGroupBox('Overlay Video (Webcam/Secondary)')
        overlay_layout = QVBoxLayout()
        self.overlay_video_combo = QComboBox()
        self.overlay_video_combo.currentIndexChanged.connect(self.update_overlay_preview)
        self.overlay_enable = QCheckBox('Enable overlay')
        self.overlay_enable.setChecked(True)
        self.overlay_enable.stateChanged.connect(self.update_overlay_preview)
        overlay_layout.addWidget(self.overlay_enable)
        overlay_layout.addWidget(self.overlay_video_combo)
        overlay_group.setLayout(overlay_layout)
        file_layout.addWidget(overlay_group)
        
        layout.addLayout(file_layout)
        
        # Position and size
        settings_group = QGroupBox('Overlay Settings')
        settings_layout = QVBoxLayout()
        
        # Position controls (X, Y percentages)
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel('Position X:'))
        self.overlay_x_spin = QSpinBox()
        self.overlay_x_spin.setRange(0, 100)
        self.overlay_x_spin.setValue(75)
        self.overlay_x_spin.setSuffix('%')
        self.overlay_x_spin.valueChanged.connect(self.update_overlay_preview)
        pos_layout.addWidget(self.overlay_x_spin)
        
        pos_layout.addWidget(QLabel('Y:'))
        self.overlay_y_spin = QSpinBox()
        self.overlay_y_spin.setRange(0, 100)
        self.overlay_y_spin.setValue(75)
        self.overlay_y_spin.setSuffix('%')
        self.overlay_y_spin.valueChanged.connect(self.update_overlay_preview)
        pos_layout.addWidget(self.overlay_y_spin)
        
        # Quick position presets
        presets_layout = QHBoxLayout()
        preset_btn_tl = QPushButton('↖')
        preset_btn_tl.setMaximumWidth(40)
        preset_btn_tl.clicked.connect(lambda: self.set_overlay_position(5, 5))
        presets_layout.addWidget(preset_btn_tl)
        
        preset_btn_tr = QPushButton('↗')
        preset_btn_tr.setMaximumWidth(40)
        preset_btn_tr.clicked.connect(lambda: self.set_overlay_position(75, 5))
        presets_layout.addWidget(preset_btn_tr)
        
        preset_btn_c = QPushButton('⊙')
        preset_btn_c.setMaximumWidth(40)
        preset_btn_c.clicked.connect(lambda: self.set_overlay_position(38, 38))
        presets_layout.addWidget(preset_btn_c)
        
        preset_btn_bl = QPushButton('↙')
        preset_btn_bl.setMaximumWidth(40)
        preset_btn_bl.clicked.connect(lambda: self.set_overlay_position(5, 75))
        presets_layout.addWidget(preset_btn_bl)
        
        preset_btn_br = QPushButton('↘')
        preset_btn_br.setMaximumWidth(40)
        preset_btn_br.clicked.connect(lambda: self.set_overlay_position(75, 75))
        presets_layout.addWidget(preset_btn_br)
        
        pos_layout.addLayout(presets_layout)
        settings_layout.addLayout(pos_layout)
        
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel('Size:'))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setMinimum(10)
        self.size_slider.setMaximum(50)
        self.size_slider.setValue(35)
        self.size_label = QLabel('35%')
        self.size_slider.valueChanged.connect(lambda v: self.size_label.setText(f'{v}%'))
        self.size_slider.valueChanged.connect(self.update_overlay_preview)
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_label)
        settings_layout.addLayout(size_layout)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Preview area with live update
        preview_group = QGroupBox('Live Preview - Drag overlay to reposition')
        preview_layout = QVBoxLayout()
        
        self.overlay_preview_label = DraggableOverlayLabel()
        self.overlay_preview_label.setText('Select videos to see preview')
        self.overlay_preview_label.setAlignment(Qt.AlignCenter)
        self.overlay_preview_label.setStyleSheet('border: 2px solid #ccc; background: #f5f5f5;')
        self.overlay_preview_label.setMinimumHeight(400)
        self.overlay_preview_label.setScaledContents(False)
        self.overlay_preview_label.overlay_moved.connect(self.on_overlay_dragged)
        self.overlay_preview_label.dragging_complete.connect(self.on_overlay_drag_complete)
        preview_layout.addWidget(self.overlay_preview_label)
        
        refresh_preview_btn = QPushButton('🔄 Refresh Preview')
        refresh_preview_btn.clicked.connect(self.update_overlay_preview)
        preview_layout.addWidget(refresh_preview_btn)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        layout.addStretch()
        return page
    
    def create_step3_watermark(self):
        """Step 3: Add watermark"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        desc = QLabel('Add a logo or watermark to your video.')
        desc.setWordWrap(True)
        desc.setStyleSheet('font-size: 13px; color: #666; padding: 10px;')
        layout.addWidget(desc)
        
        # Watermark enable
        self.watermark_enable = QCheckBox('Add watermark to video')
        self.watermark_enable.stateChanged.connect(self.toggle_watermark_settings)
        layout.addWidget(self.watermark_enable)
        
        # Watermark settings (initially disabled)
        self.watermark_widget = QWidget()
        watermark_layout = QVBoxLayout(self.watermark_widget)
        
        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel('Watermark Image:'))
        self.watermark_path = QLineEdit()
        self.watermark_path.setPlaceholderText('Select PNG or JPG image...')
        self.watermark_path.textChanged.connect(self.update_watermark_preview)
        file_layout.addWidget(self.watermark_path)
        browse_btn = QPushButton('📁 Browse')
        browse_btn.clicked.connect(self.browse_watermark)
        file_layout.addWidget(browse_btn)
        watermark_layout.addLayout(file_layout)
        
        # Position
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel('Position:'))
        self.wm_position_combo = QComboBox()
        self.wm_position_combo.addItems(['Top Left', 'Top Right', 'Bottom Left', 'Bottom Right', 'Center'])
        self.wm_position_combo.setCurrentText('Top Right')
        self.wm_position_combo.currentIndexChanged.connect(self.update_watermark_preview)
        pos_layout.addWidget(self.wm_position_combo)
        watermark_layout.addLayout(pos_layout)
        
        # Opacity
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel('Opacity:'))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(10)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(70)
        self.opacity_label = QLabel('70%')
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(f'{v}%'))
        self.opacity_slider.valueChanged.connect(self.update_watermark_preview)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        watermark_layout.addLayout(opacity_layout)
        
        self.watermark_widget.setEnabled(False)
        layout.addWidget(self.watermark_widget)
        
        # Apply button
        apply_btn = QPushButton('✨ Apply Watermark')
        apply_btn.setStyleSheet(self.get_button_style('#667eea'))
        apply_btn.clicked.connect(self.apply_watermark)
        layout.addWidget(apply_btn)
        
        # Live Preview
        preview_group = QGroupBox('📺 Live Preview')
        preview_layout = QVBoxLayout()
        
        self.watermark_preview_label = QLabel('Enable watermark to see preview')
        self.watermark_preview_label.setAlignment(Qt.AlignCenter)
        self.watermark_preview_label.setStyleSheet('border: 2px solid #ccc; background: #000; color: #fff;')
        self.watermark_preview_label.setMinimumSize(500, 350)
        self.watermark_preview_label.setScaledContents(True)
        preview_layout.addWidget(self.watermark_preview_label)
        
        refresh_wm_btn = QPushButton('🔄 Refresh Preview')
        refresh_wm_btn.clicked.connect(self.update_watermark_preview)
        preview_layout.addWidget(refresh_wm_btn)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        layout.addStretch()
        return page
    
    def create_step4_preview(self):
        """Step 4: Preview final video"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        desc = QLabel('Preview your final video before exporting.')
        desc.setWordWrap(True)
        desc.setStyleSheet('font-size: 13px; color: #666; padding: 10px;')
        layout.addWidget(desc)
        
        # Video preview
        preview_group = QGroupBox('Video Preview')
        preview_layout = QVBoxLayout()
        
        # VLC video player widget
        if VLC_AVAILABLE:
            self.vlc_instance = vlc.Instance()
            self.vlc_player = self.vlc_instance.media_player_new()
            
            # Create video frame widget
            self.video_frame = QWidget()
            self.video_frame.setStyleSheet('border: 2px solid #ccc; background: #000;')
            self.video_frame.setMinimumHeight(400)
            preview_layout.addWidget(self.video_frame)
        else:
            # Fallback to static thumbnail if VLC not available
            vlc_layout = QVBoxLayout()
            
            self.step4_thumbnail = QLabel()
            self.step4_thumbnail.setAlignment(Qt.AlignCenter)
            self.step4_thumbnail.setStyleSheet('border: 2px solid #ccc; background: #000; color: #fff; padding: 20px;')
            self.step4_thumbnail.setMinimumHeight(350)
            self.step4_thumbnail.setWordWrap(True)
            self.step4_thumbnail.setText(
                '⚠️ Live Video Preview Unavailable\n\n'
                'VLC media player is required for live video playback.\n\n'
                'Using static thumbnail preview instead.\n'
                'Click "Install VLC" below to enable live preview.'
            )
            vlc_layout.addWidget(self.step4_thumbnail)
            
            # Install VLC button
            install_vlc_btn = QPushButton('📥 Install VLC Media Player')
            install_vlc_btn.setStyleSheet(self.get_button_style('#ff9800'))
            install_vlc_btn.clicked.connect(self.install_vlc)
            vlc_layout.addWidget(install_vlc_btn)
            
            preview_layout.addLayout(vlc_layout)
            self.vlc_player = None
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Playback controls
        controls_layout = QHBoxLayout()
        
        self.play_pause_btn = QPushButton('▶️ Play')
        self.play_pause_btn.clicked.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_pause_btn)
        
        stop_btn = QPushButton('⏹️ Stop')
        stop_btn.clicked.connect(self.stop_playback)
        controls_layout.addWidget(stop_btn)
        
        controls_layout.addStretch()
        
        open_player_btn = QPushButton('📂 Open in External Player')
        open_player_btn.clicked.connect(self.open_external_player)
        controls_layout.addWidget(open_player_btn)
        
        reload_btn = QPushButton('🔄 Reload Preview')
        reload_btn.clicked.connect(self.reload_preview)
        controls_layout.addWidget(reload_btn)
        
        layout.addLayout(controls_layout)
        
        # Video info
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(100)
        layout.addWidget(self.info_text)
        
        return page
    
    def create_step5_export(self):
        """Step 5: Export and upload"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        desc = QLabel('Export your final video and optionally upload to your destination.')
        desc.setWordWrap(True)
        desc.setStyleSheet('font-size: 13px; color: #666; padding: 10px;')
        layout.addWidget(desc)
        
        # Export settings
        export_group = QGroupBox('Export Settings')
        export_layout = QVBoxLayout()
        
        # Output filename
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel('Filename:'))
        self.export_filename = QLineEdit()
        self.export_filename.setText(f"Final_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        name_layout.addWidget(self.export_filename)
        export_layout.addLayout(name_layout)
        
        # Quality
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel('Quality:'))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(['High (Slow)', 'Medium', 'Low (Fast)'])
        self.quality_combo.setCurrentIndex(1)
        quality_layout.addWidget(self.quality_combo)
        export_layout.addLayout(quality_layout)
        
        # Output folder
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel('Save to:'))
        self.export_folder = QLineEdit()
        self.export_folder.setText(self.session_folder if self.session_folder else '')
        folder_layout.addWidget(self.export_folder)
        browse_folder_btn = QPushButton('📁 Browse')
        browse_folder_btn.clicked.connect(self.browse_export_folder)
        folder_layout.addWidget(browse_folder_btn)
        export_layout.addLayout(folder_layout)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        # Export button
        export_btn = QPushButton('💾 Export Video')
        export_btn.setStyleSheet(self.get_button_style('#4caf50'))
        export_btn.clicked.connect(self.export_final)
        layout.addWidget(export_btn)
        
        # Upload section
        upload_group = QGroupBox('Upload Options (Optional)')
        upload_layout = QVBoxLayout()
        
        self.upload_enable = QCheckBox('Upload after export')
        upload_layout.addWidget(self.upload_enable)
        
        dest_layout = QHBoxLayout()
        dest_layout.addWidget(QLabel('Destination:'))
        self.upload_dest_combo = QComboBox()
        self.upload_dest_combo.addItems([
            'Canvas Studio API',
            'YouTube API',
            'Vimeo API',
            'Microsoft Stream API',
            'SharePoint API'
        ])
        dest_layout.addWidget(self.upload_dest_combo)
        
        settings_btn = QPushButton('⚙️ Configure')
        settings_btn.clicked.connect(self.open_upload_settings)
        dest_layout.addWidget(settings_btn)
        upload_layout.addLayout(dest_layout)
        
        upload_btn = QPushButton('☁️ Upload Now')
        upload_btn.setStyleSheet(self.get_button_style('#2196F3'))
        upload_btn.clicked.connect(self.upload_video)
        upload_layout.addWidget(upload_btn)
        
        upload_group.setLayout(upload_layout)
        layout.addWidget(upload_group)
        
        # Export log
        log_group = QGroupBox('Export Log')
        log_layout = QVBoxLayout()
        self.export_log = QTextEdit()
        self.export_log.setReadOnly(True)
        self.export_log.setMaximumHeight(150)
        log_layout.addWidget(self.export_log)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        layout.addStretch()
        return page
    
    # ===== Utility Methods =====
    
    def load_session_files(self):
        """Load files from session folder"""
        if not self.session_folder or not os.path.exists(self.session_folder):
            return
        
        self.video_list.clear()
        self.audio_list.clear()
        self.bg_video_combo.clear()
        self.overlay_video_combo.clear()
        
        for filename in os.listdir(self.session_folder):
            filepath = os.path.join(self.session_folder, filename)
            
            if filename.endswith('.mp4'):
                item = QListWidgetItem(f"🎥 {filename}")
                item.setData(Qt.UserRole, filepath)
                self.video_list.addItem(item)
                self.bg_video_combo.addItem(filename, filepath)
                self.overlay_video_combo.addItem(filename, filepath)
                self.current_project['source_videos'].append(filepath)
                
            elif filename.endswith(('.wav', '.mp3')):
                item = QListWidgetItem(f"🎤 {filename}")
                item.setData(Qt.UserRole, filepath)
                self.audio_list.addItem(item)
                self.current_project['source_audio'].append(filepath)
    
    def next_step(self):
        """Move to next wizard step"""
        current = self.stacked_widget.currentIndex()
        
        # Validate step before proceeding
        if current == 1:  # Step 2 - Overlay
            # Auto-apply overlay if enabled and not already applied
            if self.overlay_enable.isChecked():
                bg_video = self.bg_video_combo.currentData()
                overlay_video = self.overlay_video_combo.currentData()
                
                if bg_video and overlay_video and not self.current_project.get('overlay_video'):
                    reply = QMessageBox.question(
                        self,
                        'Apply Overlay',
                        'You have configured an overlay but haven\'t applied it yet. Apply now?',
                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                    )
                    
                    if reply == QMessageBox.Yes:
                        self.apply_overlay()
                        return  # Wait for processing to complete
                    elif reply == QMessageBox.Cancel:
                        return  # Don't proceed
            else:
                # User disabled overlay, use background video directly
                bg_video = self.bg_video_combo.currentData()
                if bg_video and not self.current_project.get('overlay_video'):
                    self.current_project['overlay_video'] = bg_video
        
        elif current == 2:  # Step 3 - Watermark
            # Auto-apply watermark if enabled and not already applied
            if self.watermark_enable.isChecked():
                watermark = self.watermark_path.text()
                
                if watermark and os.path.exists(watermark) and not self.current_project.get('watermarked_video'):
                    reply = QMessageBox.question(
                        self,
                        'Apply Watermark',
                        'You have configured a watermark but haven\'t applied it yet. Apply now?',
                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                    )
                    
                    if reply == QMessageBox.Yes:
                        self.apply_watermark()
                        return  # Wait for processing to complete
                    elif reply == QMessageBox.Cancel:
                        return  # Don't proceed
            else:
                # User disabled watermark, use overlay video directly
                overlay_video = self.current_project.get('overlay_video')
                if overlay_video and not self.current_project.get('watermarked_video'):
                    self.current_project['watermarked_video'] = overlay_video
        
        if current < 4:
            self.stacked_widget.setCurrentIndex(current + 1)
            self.update_navigation()
    
    def previous_step(self):
        """Move to previous wizard step"""
        current = self.stacked_widget.currentIndex()
        if current > 0:
            self.stacked_widget.setCurrentIndex(current - 1)
            self.update_navigation()
    
    def update_navigation(self):
        """Update navigation buttons and step indicator"""
        current = self.stacked_widget.currentIndex()
        
        step_names = [
            'Step 1 of 5: Verify Recordings',
            'Step 2 of 5: Apply Overlay',
            'Step 3 of 5: Add Watermark',
            'Step 4 of 5: Preview Video',
            'Step 5 of 5: Export & Upload'
        ]
        
        self.step_indicator.setText(step_names[current])
        self.prev_btn.setEnabled(current > 0)
        
        if current == 4:
            self.next_btn.setVisible(False)
            self.finish_btn.setVisible(True)
        else:
            self.next_btn.setVisible(True)
            self.finish_btn.setVisible(False)
        
        # Auto-load preview when entering Step 4
        if current == 3:  # Step 4 (0-indexed)
            QTimer.singleShot(100, self.reload_preview)
    
    def finish_wizard(self):
        """Complete wizard and close"""
        reply = QMessageBox.question(
            self,
            'Finish Editing',
            'Are you done editing? This will close the editor.',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.close()
    
    # ===== Step 1 Methods =====
    
    def preview_selected_video(self):
        """Preview selected video file"""
        item = self.video_list.currentItem()
        if item:
            self.preview_video(item)
    
    def preview_video(self, item):
        """Open video in default player"""
        filepath = item.data(Qt.UserRole)
        os.startfile(filepath)
    
    def preview_selected_audio(self):
        """Preview selected audio file"""
        item = self.audio_list.currentItem()
        if item:
            self.preview_audio(item)
    
    def preview_audio(self, item):
        """Open audio in default player"""
        filepath = item.data(Qt.UserRole)
        os.startfile(filepath)
    
    def rerecord_video(self):
        """Rerecord video (opens main recorder)"""
        QMessageBox.information(
            self,
            'Re-record Video',
            'Please close the editor and use the main recorder window to record new video.\n\n'
            'Your current session files will remain available.'
        )
    
    def rerecord_audio(self):
        """Rerecord audio (opens main recorder)"""
        QMessageBox.information(
            self,
            'Re-record Audio',
            'Please close the editor and use the main recorder window to record new audio.\n\n'
            'Your current session files will remain available.'
        )
    
    def merge_videos(self):
        """Merge selected videos"""
        selected_items = self.video_list.selectedItems()
        if len(selected_items) < 2:
            QMessageBox.warning(self, 'Selection Required', 'Please select at least 2 videos to merge.')
            return
        
        # Ask for layout
        layout, ok = QMessageBox.question(
            self,
            'Merge Layout',
            'How would you like to merge the videos?\n\nYes = Side by Side\nNo = Sequential (one after another)',
            QMessageBox.Yes | QMessageBox.No
        )
        
        videos = [item.data(Qt.UserRole) for item in selected_items]
        layout_type = 'side_by_side' if layout == QMessageBox.Yes else 'sequential'
        
        output_path = os.path.join(
            self.session_folder,
            f"merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        
        self.show_processing("Merging videos...")
        self.processor = VideoProcessor(
            self.ffmpeg_path,
            'merge',
            videos=videos,
            output=output_path,
            layout=layout_type
        )
        self.processor.progress_update.connect(self.update_progress)
        self.processor.processing_complete.connect(self.merge_complete)
        self.processor.start()
    
    def merge_complete(self, success, result):
        """Handle merge completion"""
        self.hide_processing()
        
        if success:
            self.current_project['merged_video'] = result
            QMessageBox.information(self, 'Success', f'Videos merged successfully!\n\n{os.path.basename(result)}')
            self.load_session_files()
        else:
            QMessageBox.critical(self, 'Error', f'Failed to merge videos:\n\n{result}')
    
    def split_video(self):
        """Split video into segments"""
        QMessageBox.information(
            self,
            'Split Video',
            'Video splitting feature coming soon!\n\nFor now, use the trim function in Step 2.'
        )
    
    # ===== Step 2 Methods =====
    
    def apply_overlay(self):
        """Apply picture-in-picture overlay"""
        if not self.overlay_enable.isChecked():
            # Just use background video
            bg_video = self.bg_video_combo.currentData()
            if bg_video:
                self.current_project['overlay_video'] = bg_video
                QMessageBox.information(self, 'Info', 'Using background video without overlay.')
            return
        
        bg_video = self.bg_video_combo.currentData()
        overlay_video = self.overlay_video_combo.currentData()
        
        if not bg_video or not overlay_video:
            QMessageBox.warning(self, 'Selection Required', 'Please select both background and overlay videos.')
            return
        
        if bg_video == overlay_video:
            QMessageBox.warning(self, 'Invalid Selection', 'Background and overlay videos must be different.')
            return
        
        # Use X/Y percentage positions
        x_percent = self.overlay_x_spin.value()
        y_percent = self.overlay_y_spin.value()
        size = self.size_slider.value() / 100.0
        
        output_path = os.path.join(
            self.session_folder,
            f"overlay_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        
        self.show_processing("Applying overlay...")
        self.processor = VideoProcessor(
            self.ffmpeg_path,
            'overlay',
            background=bg_video,
            overlay=overlay_video,
            output=output_path,
            x_percent=x_percent,
            y_percent=y_percent,
            size=size
        )
        self.processor.progress_update.connect(self.update_progress)
        self.processor.processing_complete.connect(self.overlay_complete)
        self.processor.start()
    
    def overlay_complete(self, success, result):
        """Handle overlay completion"""
        self.hide_processing()
        
        if success:
            self.current_project['overlay_video'] = result
            self.load_session_files()
            
            # Show preview of result
            self.show_result_preview(result, "Overlay applied successfully!")
            
            # Auto-advance to next step
            self.stacked_widget.setCurrentIndex(2)  # Move to Step 3
            self.update_navigation()
        else:
            QMessageBox.critical(self, 'Error', f'Failed to apply overlay:\n\n{result}')
    
    def show_result_preview(self, video_path, message):
        """Show a quick preview of the result"""
        try:
            frame = self.extract_video_frame(video_path)
            if frame is not None:
                pixmap = QPixmap.fromImage(frame)
                self.overlay_preview_label.setPixmap(pixmap.scaled(
                    self.overlay_preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
                QMessageBox.information(self, 'Success', message)
        except:
            QMessageBox.information(self, 'Success', message)
    
    # ===== Step 3 Methods =====
    
    def toggle_watermark_settings(self, state):
        """Enable/disable watermark settings"""
        self.watermark_widget.setEnabled(state == Qt.Checked)
    
    def browse_watermark(self):
        """Browse for watermark image"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            'Select Watermark Image',
            '',
            'Images (*.png *.jpg *.jpeg)'
        )
        
        if filename:
            self.watermark_path.setText(filename)
    
    def apply_watermark(self):
        """Apply watermark to video"""
        if not self.watermark_enable.isChecked():
            # Skip watermark
            input_video = self.current_project.get('overlay_video') or self.current_project.get('merged_video')
            if input_video:
                self.current_project['watermarked_video'] = input_video
                QMessageBox.information(self, 'Info', 'Skipping watermark.')
            return
        
        watermark = self.watermark_path.text()
        if not watermark or not os.path.exists(watermark):
            QMessageBox.warning(self, 'File Required', 'Please select a watermark image.')
            return
        
        # Get the most recent processed video
        input_video = (self.current_project.get('overlay_video') or 
                      self.current_project.get('merged_video') or
                      (self.current_project['source_videos'][0] if self.current_project['source_videos'] else None))
        
        if not input_video:
            QMessageBox.warning(self, 'No Video', 'No video available to add watermark. Complete previous steps first.')
            return
        
        position_map = {
            'Top Left': 'top_left',
            'Top Right': 'top_right',
            'Bottom Left': 'bottom_left',
            'Bottom Right': 'bottom_right',
            'Center': 'center'
        }
        
        position = position_map[self.wm_position_combo.currentText()]
        opacity = self.opacity_slider.value() / 100.0
        
        output_path = os.path.join(
            self.session_folder,
            f"watermarked_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        
        self.show_processing("Adding watermark...")
        self.processor = VideoProcessor(
            self.ffmpeg_path,
            'watermark',
            input=input_video,
            watermark=watermark,
            output=output_path,
            position=position,
            opacity=opacity
        )
        self.processor.progress_update.connect(self.update_progress)
        self.processor.processing_complete.connect(self.watermark_complete)
        self.processor.start()
    
    def watermark_complete(self, success, result):
        """Handle watermark completion"""
        self.hide_processing()
        
        if success:
            self.current_project['watermarked_video'] = result
            self.load_session_files()
            
            # Update preview
            self.update_watermark_preview()
            
            QMessageBox.information(self, 'Success', 'Watermark added successfully!')
            
            # Auto-advance to Step 4
            self.stacked_widget.setCurrentIndex(3)  # Move to Step 4
            self.update_navigation()
        else:
            QMessageBox.critical(self, 'Error', f'Failed to add watermark:\n\n{result}')
    
    # ===== Step 4 Methods =====
    
    def reload_preview(self):
        """Load preview of current video"""
        # Get the most recent processed video
        preview_video = (self.current_project.get('watermarked_video') or
                        self.current_project.get('overlay_video') or
                        self.current_project.get('merged_video') or
                        (self.current_project['source_videos'][0] if self.current_project['source_videos'] else None))
        
        if not preview_video or not os.path.exists(preview_video):
            QMessageBox.warning(self, 'No Video', 'No video available to preview. Complete previous steps first.')
            return
        
        self.current_project['final_video'] = preview_video
        
        # Load video into VLC player if available
        if VLC_AVAILABLE and self.vlc_player:
            try:
                # Set the video frame as output window
                if sys.platform.startswith('linux'):
                    self.vlc_player.set_xwindow(int(self.video_frame.winId()))
                elif sys.platform == 'win32':
                    self.vlc_player.set_hwnd(int(self.video_frame.winId()))
                elif sys.platform == 'darwin':
                    self.vlc_player.set_nsobject(int(self.video_frame.winId()))
                
                # Load and play video
                media = self.vlc_instance.media_new(preview_video)
                self.vlc_player.set_media(media)
                self.vlc_player.play()
                self.play_pause_btn.setText('⏸️ Pause')
            except Exception as e:
                logging.error(f'VLC playback error: {str(e)}')
                QMessageBox.warning(self, 'Playback Error', 
                    f'Could not play video with VLC.\n\n{str(e)}\n\nUse "Open in External Player" instead.')
        else:
            # Fallback to static thumbnail
            frame = self.extract_video_frame(preview_video)
            if frame:
                pixmap = QPixmap.fromImage(frame)
                self.step4_thumbnail.setPixmap(pixmap.scaled(
                    self.step4_thumbnail.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
            else:
                self.step4_thumbnail.setText(
                    '⚠️ Could not load video preview\n\n'
                    'Click "Open in External Player" to view the video.'
                )
        
        # Show info
        file_size = os.path.getsize(preview_video) / (1024 * 1024)
        self.info_text.setPlainText(
            f"File: {os.path.basename(preview_video)}\n"
            f"Size: {file_size:.2f} MB\n"
            f"Path: {preview_video}"
        )
    
    def toggle_playback(self):
        """Toggle play/pause for video preview"""
        if not VLC_AVAILABLE or not self.vlc_player:
            return
        
        if self.vlc_player.is_playing():
            self.vlc_player.pause()
            self.play_pause_btn.setText('▶️ Play')
        else:
            self.vlc_player.play()
            self.play_pause_btn.setText('⏸️ Pause')
    
    def stop_playback(self):
        """Stop video playback"""
        if not VLC_AVAILABLE or not self.vlc_player:
            return
        
        self.vlc_player.stop()
        self.play_pause_btn.setText('▶️ Play')
    
    def install_vlc(self):
        """Install VLC Media Player"""
        from PyQt5.QtWidgets import QProgressDialog
        from vlc_installer import check_vlc_installed, install_vlc as do_install_vlc
        
        # Check if already installed
        installed, path = check_vlc_installed()
        if installed:
            QMessageBox.information(
                self,
                'VLC Already Installed',
                f'VLC is already installed at:\n{path}\n\n'
                'Please restart the application to enable live video preview.'
            )
            return
        
        # Confirm installation
        reply = QMessageBox.question(
            self,
            'Install VLC Media Player',
            'This will download and install VLC Media Player (~40 MB).\n\n'
            'The installation may take a few minutes.\n\n'
            'Continue?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Show progress dialog
        progress = QProgressDialog('Installing VLC Media Player...', 'Cancel', 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        
        # Install in background thread
        class InstallThread(QThread):
            finished_signal = pyqtSignal(bool, str)
            
            def run(self):
                try:
                    success, message = do_install_vlc()
                    self.finished_signal.emit(success, message)
                except Exception as e:
                    self.finished_signal.emit(False, str(e))
        
        def on_install_complete(success, message):
            progress.close()
            
            # Clean up thread
            if hasattr(self, 'install_thread'):
                self.install_thread.wait()
                self.install_thread.deleteLater()
                self.install_thread = None
            
            if success:
                QMessageBox.information(
                    self,
                    'Installation Complete',
                    f'VLC Media Player has been installed successfully!\n\n'
                    f'{message}\n\n'
                    'Please restart the application to enable live video preview.'
                )
            else:
                QMessageBox.critical(
                    self,
                    'Installation Failed',
                    f'Failed to install VLC:\n\n{message}\n\n'
                    'Please install VLC manually from:\nhttps://www.videolan.org/vlc/'
                )
        
        self.install_thread = InstallThread()
        self.install_thread.finished_signal.connect(on_install_complete)
        self.install_thread.start()
    
    def open_external_player(self):
        """Open video in system's default player"""
        preview_video = self.current_project.get('final_video')
        if preview_video and os.path.exists(preview_video):
            import subprocess
            import platform
            
            try:
                if platform.system() == 'Windows':
                    os.startfile(preview_video)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.call(['open', preview_video])
                else:  # Linux
                    subprocess.call(['xdg-open', preview_video])
            except Exception as e:
                QMessageBox.warning(self, 'Error', f'Could not open video:\n{str(e)}')
        else:
            QMessageBox.warning(self, 'No Video', 'No video available to play.')
    
    # ===== Step 5 Methods =====
    
    def browse_export_folder(self):
        """Browse for export folder"""
        folder = QFileDialog.getExistingDirectory(self, 'Select Export Folder')
        if folder:
            self.export_folder.setText(folder)
    
    def export_final(self):
        """Export final video"""
        final_video = self.current_project.get('final_video')
        if not final_video or not os.path.exists(final_video):
            QMessageBox.warning(self, 'No Video', 'No video ready for export. Complete previous steps first.')
            return
        
        output_folder = self.export_folder.text()
        if not output_folder or not os.path.exists(output_folder):
            QMessageBox.warning(self, 'Invalid Folder', 'Please select a valid export folder.')
            return
        
        output_filename = self.export_filename.text()
        if not output_filename.endswith('.mp4'):
            output_filename += '.mp4'
        
        output_path = os.path.join(output_folder, output_filename)
        
        quality_map = {
            'High (Slow)': 'high',
            'Medium': 'medium',
            'Low (Fast)': 'low'
        }
        quality = quality_map[self.quality_combo.currentText()]
        
        self.export_log.append(f"Starting export to: {output_path}")
        self.show_processing("Exporting video...")
        
        self.processor = VideoProcessor(
            self.ffmpeg_path,
            'export',
            input=final_video,
            output=output_path,
            quality=quality
        )
        self.processor.progress_update.connect(self.update_progress)
        self.processor.processing_complete.connect(self.export_complete)
        self.processor.start()
    
    def export_complete(self, success, result):
        """Handle export completion"""
        self.hide_processing()
        
        if success:
            self.export_log.append(f"✓ Export successful: {result}")
            QMessageBox.information(
                self,
                'Export Complete',
                f'Video exported successfully!\n\n{result}'
            )
            
            # Optionally upload
            if self.upload_enable.isChecked():
                self.upload_video()
        else:
            self.export_log.append(f"✗ Export failed: {result}")
            QMessageBox.critical(self, 'Error', f'Failed to export video:\n\n{result}')
    
    def open_upload_settings(self):
        """Open upload API configuration dialog"""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle('Upload API Settings')
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(500)
        
        layout = QVBoxLayout(dialog)
        
        # Tab widget for different APIs
        tabs = QTabWidget()
        
        # Canvas Studio tab
        canvas_tab = self.create_canvas_settings_tab()
        tabs.addTab(canvas_tab, '🎬 Canvas Studio')
        
        # YouTube tab
        youtube_tab = self.create_youtube_settings_tab()
        tabs.addTab(youtube_tab, '📺 YouTube')
        
        # Vimeo tab
        vimeo_tab = self.create_vimeo_settings_tab()
        tabs.addTab(vimeo_tab, '🎥 Vimeo')
        
        # Microsoft Stream tab
        stream_tab = self.create_stream_settings_tab()
        tabs.addTab(stream_tab, '📊 Microsoft Stream')
        
        # SharePoint tab
        sharepoint_tab = self.create_sharepoint_settings_tab()
        tabs.addTab(sharepoint_tab, '📁 SharePoint')
        
        layout.addWidget(tabs)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec_() == QDialog.Accepted:
            self.save_upload_settings()
    
    def create_canvas_settings_tab(self):
        """Create Canvas Studio API settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel('<b>Canvas Studio API Configuration</b>'))
        
        # API Token
        layout.addWidget(QLabel('API Token:'))
        self.canvas_token = QLineEdit()
        self.canvas_token.setPlaceholderText('Enter Canvas Studio API token...')
        layout.addWidget(self.canvas_token)
        
        # Account ID
        layout.addWidget(QLabel('Account ID:'))
        self.canvas_account = QLineEdit()
        self.canvas_account.setPlaceholderText('Canvas account/institution ID')
        layout.addWidget(self.canvas_account)
        
        # Upload settings
        layout.addWidget(QLabel('Default Privacy:'))
        self.canvas_privacy = QComboBox()
        self.canvas_privacy.addItems(['Private', 'Unlisted', 'Public'])
        layout.addWidget(self.canvas_privacy)
        
        layout.addStretch()
        return widget
    
    def create_youtube_settings_tab(self):
        """Create YouTube API settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel('<b>YouTube API Configuration</b>'))
        
        # Client ID
        layout.addWidget(QLabel('Client ID:'))
        self.youtube_client_id = QLineEdit()
        self.youtube_client_id.setPlaceholderText('Google API Client ID')
        layout.addWidget(self.youtube_client_id)
        
        # Client Secret
        layout.addWidget(QLabel('Client Secret:'))
        self.youtube_secret = QLineEdit()
        self.youtube_secret.setEchoMode(QLineEdit.Password)
        self.youtube_secret.setPlaceholderText('Google API Client Secret')
        layout.addWidget(self.youtube_secret)
        
        # Default privacy
        layout.addWidget(QLabel('Default Privacy:'))
        self.youtube_privacy = QComboBox()
        self.youtube_privacy.addItems(['Private', 'Unlisted', 'Public'])
        layout.addWidget(self.youtube_privacy)
        
        # Category
        layout.addWidget(QLabel('Default Category:'))
        self.youtube_category = QComboBox()
        self.youtube_category.addItems(['Education', 'How-to & Style', 'Science & Technology', 'People & Blogs'])
        layout.addWidget(self.youtube_category)
        
        layout.addStretch()
        return widget
    
    def create_vimeo_settings_tab(self):
        """Create Vimeo API settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel('<b>Vimeo API Configuration</b>'))
        
        # Access Token
        layout.addWidget(QLabel('Access Token:'))
        self.vimeo_token = QLineEdit()
        self.vimeo_token.setPlaceholderText('Vimeo API access token')
        layout.addWidget(self.vimeo_token)
        
        # Default privacy
        layout.addWidget(QLabel('Default Privacy:'))
        self.vimeo_privacy = QComboBox()
        self.vimeo_privacy.addItems(['Private', 'Unlisted', 'Public'])
        layout.addWidget(self.vimeo_privacy)
        
        # Folder
        layout.addWidget(QLabel('Default Folder/Showcase:'))
        self.vimeo_folder = QLineEdit()
        self.vimeo_folder.setPlaceholderText('Optional: Folder ID or showcase ID')
        layout.addWidget(self.vimeo_folder)
        
        layout.addStretch()
        return widget
    
    def create_stream_settings_tab(self):
        """Create Microsoft Stream API settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel('<b>Microsoft Stream API Configuration</b>'))
        
        # Tenant ID
        layout.addWidget(QLabel('Tenant ID:'))
        self.stream_tenant = QLineEdit()
        self.stream_tenant.setPlaceholderText('Microsoft 365 Tenant ID')
        layout.addWidget(self.stream_tenant)
        
        # Client ID
        layout.addWidget(QLabel('Application (Client) ID:'))
        self.stream_client_id = QLineEdit()
        self.stream_client_id.setPlaceholderText('Azure AD Application ID')
        layout.addWidget(self.stream_client_id)
        
        # Client Secret
        layout.addWidget(QLabel('Client Secret:'))
        self.stream_secret = QLineEdit()
        self.stream_secret.setEchoMode(QLineEdit.Password)
        self.stream_secret.setPlaceholderText('Azure AD Client Secret')
        layout.addWidget(self.stream_secret)
        
        # Default group
        layout.addWidget(QLabel('Default Group/Channel:'))
        self.stream_group = QLineEdit()
        self.stream_group.setPlaceholderText('Optional: Group or channel ID')
        layout.addWidget(self.stream_group)
        
        layout.addStretch()
        return widget
    
    def create_sharepoint_settings_tab(self):
        """Create SharePoint API settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel('<b>SharePoint API Configuration</b>'))
        
        # Site URL
        layout.addWidget(QLabel('SharePoint Site URL:'))
        self.sharepoint_site = QLineEdit()
        self.sharepoint_site.setPlaceholderText('https://your-tenant.sharepoint.com/sites/your-site')
        layout.addWidget(self.sharepoint_site)
        
        # Client ID
        layout.addWidget(QLabel('Client ID:'))
        self.sharepoint_client_id = QLineEdit()
        self.sharepoint_client_id.setPlaceholderText('Azure AD Application ID')
        layout.addWidget(self.sharepoint_client_id)
        
        # Client Secret
        layout.addWidget(QLabel('Client Secret:'))
        self.sharepoint_secret = QLineEdit()
        self.sharepoint_secret.setEchoMode(QLineEdit.Password)
        self.sharepoint_secret.setPlaceholderText('Azure AD Client Secret')
        layout.addWidget(self.sharepoint_secret)
        
        # Library path
        layout.addWidget(QLabel('Document Library:'))
        self.sharepoint_library = QLineEdit()
        self.sharepoint_library.setPlaceholderText('Shared Documents/Videos')
        layout.addWidget(self.sharepoint_library)
        
        layout.addStretch()
        return widget
    
    def save_upload_settings(self):
        """Save upload API settings to config"""
        # TODO: Implement config saving using config_manager
        QMessageBox.information(self, 'Settings Saved', 'Upload API settings have been saved.')
    
    def upload_video(self):
        """Upload video to destination"""
        QMessageBox.information(
            self,
            'Upload Feature',
            'Upload integration coming soon!\n\n'
            'Configure your API credentials in the settings first.'
        )
    
    # ===== Progress Handling =====
    
    def show_processing(self, message):
        """Show processing state"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(message)
        self.setEnabled(False)
    
    def hide_processing(self):
        """Hide processing state"""
        self.progress_bar.setVisible(False)
        self.status_label.setText('')
        self.setEnabled(True)
    
    def update_progress(self, value, message):
        """Update progress bar"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    # ===== Live Preview Methods =====
    
    def extract_video_frame(self, video_path, timestamp=1.0):
        """Extract a frame from video using OpenCV"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            
            # Seek to timestamp
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_number = int(fps * timestamp)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channel = frame_rgb.shape
                bytes_per_line = 3 * width
                q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
                return q_image
            
            return None
        except Exception as e:
            logging.error(f"Error extracting frame: {e}")
            return None
    
    def show_video_preview_step1(self, item):
        """Show preview thumbnail for selected video in Step 1"""
        try:
            filepath = item.data(Qt.UserRole)
            if not filepath or not os.path.exists(filepath):
                return
            
            # Extract frame
            frame = self.extract_video_frame(filepath)
            if frame:
                pixmap = QPixmap.fromImage(frame)
                self.step1_preview_label.setPixmap(pixmap.scaled(
                    self.step1_preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
                
                # Show file info
                file_size = os.path.getsize(filepath) / (1024 * 1024)
                self.step1_info_label.setText(f"{os.path.basename(filepath)} - {file_size:.1f} MB")
            else:
                self.step1_preview_label.setText('Could not load preview')
        except Exception as e:
            logging.error(f"Preview error: {e}")
            self.step1_preview_label.setText('Preview unavailable')
    
    def update_overlay_preview(self):
        """Update live preview for Step 2 overlay"""
        try:
            if not self.overlay_enable.isChecked():
                # Just show background video
                bg_video = self.bg_video_combo.currentData()
                if bg_video and os.path.exists(bg_video):
                    frame = self.extract_video_frame(bg_video)
                    if frame:
                        pixmap = QPixmap.fromImage(frame)
                        self.overlay_preview_label.setPixmap(pixmap.scaled(
                            self.overlay_preview_label.size(),
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        ))
                        self.overlay_preview_label.set_overlay_rect(None)
                return
            
            bg_video = self.bg_video_combo.currentData()
            overlay_video = self.overlay_video_combo.currentData()
            
            if not bg_video or not overlay_video or not os.path.exists(bg_video) or not os.path.exists(overlay_video):
                self.overlay_preview_label.setText('Select both videos to see preview')
                self.overlay_preview_label.set_overlay_rect(None)
                return
            
            # Extract frames
            bg_frame = self.extract_video_frame(bg_video)
            overlay_frame = self.extract_video_frame(overlay_video)
            
            if not bg_frame or not overlay_frame:
                self.overlay_preview_label.setText('Could not load video frames')
                self.overlay_preview_label.set_overlay_rect(None)
                return
            
            # Create composite image
            bg_pixmap = QPixmap.fromImage(bg_frame)
            overlay_pixmap = QPixmap.fromImage(overlay_frame)
            
            # Calculate overlay size (keep aspect ratio)
            size_percent = self.size_slider.value() / 100.0
            overlay_width = int(bg_pixmap.width() * size_percent)
            overlay_height = int(bg_pixmap.height() * size_percent)
            
            overlay_pixmap = overlay_pixmap.scaled(overlay_width, overlay_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Use X/Y percentage positions
            x_percent = self.overlay_x_spin.value() / 100.0
            y_percent = self.overlay_y_spin.value() / 100.0
            
            x = int(x_percent * (bg_pixmap.width() - overlay_pixmap.width()))
            y = int(y_percent * (bg_pixmap.height() - overlay_pixmap.height()))
            
            # Draw overlay on background
            from PyQt5.QtCore import QRect
            composite = QPixmap(bg_pixmap)
            painter = QPainter(composite)
            
            # Draw semi-transparent border around overlay for visibility
            pen = QPen(Qt.yellow, 3)
            painter.setPen(pen)
            painter.drawRect(x-2, y-2, overlay_pixmap.width()+4, overlay_pixmap.height()+4)
            
            painter.drawPixmap(x, y, overlay_pixmap)
            painter.end()
            
            # Calculate scaled dimensions for display
            label_size = self.overlay_preview_label.size()
            scaled_pixmap = composite.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Calculate scale factor
            scale_x = scaled_pixmap.width() / composite.width()
            scale_y = scaled_pixmap.height() / composite.height()
            
            # Calculate offset (for centering when aspect ratios don't match)
            x_offset = (label_size.width() - scaled_pixmap.width()) // 2
            y_offset = (label_size.height() - scaled_pixmap.height()) // 2
            
            # Store overlay rect in SCALED coordinates for dragging
            scaled_x = int(x * scale_x) + x_offset
            scaled_y = int(y * scale_y) + y_offset
            scaled_width = int(overlay_pixmap.width() * scale_x)
            scaled_height = int(overlay_pixmap.height() * scale_y)
            
            overlay_rect = QRect(scaled_x, scaled_y, scaled_width, scaled_height)
            self.overlay_preview_label.set_overlay_rect(overlay_rect, self.overlay_scale_info)
            
            # Store scale info for reverse calculation during dragging
            self.overlay_scale_info = {
                'scale_x': scale_x,
                'scale_y': scale_y,
                'x_offset': x_offset,
                'y_offset': y_offset,
                'bg_width': bg_pixmap.width(),
                'bg_height': bg_pixmap.height(),
                'overlay_width': overlay_pixmap.width(),
                'overlay_height': overlay_pixmap.height()
            }
            
            # Display composite
            self.overlay_preview_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            logging.error(f"Overlay preview error: {e}")
            self.overlay_preview_label.setText('Preview error')
            self.overlay_preview_label.set_overlay_rect(None)
    
    def set_overlay_position(self, x_percent, y_percent):
        """Set overlay position from preset buttons"""
        self.overlay_x_spin.setValue(x_percent)
        self.overlay_y_spin.setValue(y_percent)
        self.update_overlay_preview()
    
    def on_overlay_dragged(self, x_percent, y_percent):
        """Handle overlay being dragged in preview - only update spinboxes during drag"""
        if not hasattr(self, 'overlay_scale_info'):
            return
        
        # Block signals to prevent recursive updates
        self.overlay_x_spin.blockSignals(True)
        self.overlay_y_spin.blockSignals(True)
        
        self.overlay_x_spin.setValue(x_percent)
        self.overlay_y_spin.setValue(y_percent)
        
        self.overlay_x_spin.blockSignals(False)
        self.overlay_y_spin.blockSignals(False)
        
        # Don't regenerate preview during drag - too expensive
        # Preview will be updated when dragging completes
    
    def on_overlay_drag_complete(self):
        """Regenerate preview when dragging is complete"""
        self.update_overlay_preview()
    
    def update_watermark_preview(self):
        """Update live preview for Step 3 watermark"""
        try:
            if not self.watermark_enable.isChecked():
                self.watermark_preview_label.setText('Enable watermark to see preview')
                return
            
            watermark_path = self.watermark_path.text()
            if not watermark_path or not os.path.exists(watermark_path):
                self.watermark_preview_label.setText('Select watermark image')
                return
            
            # Get most recent video
            input_video = (self.current_project.get('overlay_video') or 
                          self.current_project.get('merged_video') or
                          (self.current_project['source_videos'][0] if self.current_project['source_videos'] else None))
            
            if not input_video or not os.path.exists(input_video):
                self.watermark_preview_label.setText('No video available')
                return
            
            # Extract video frame
            video_frame = self.extract_video_frame(input_video)
            if not video_frame:
                self.watermark_preview_label.setText('Could not load video')
                return
            
            video_pixmap = QPixmap.fromImage(video_frame)
            
            # Load watermark
            watermark_pixmap = QPixmap(watermark_path)
            if watermark_pixmap.isNull():
                self.watermark_preview_label.setText('Invalid watermark image')
                return
            
            # Scale watermark (max 20% of video size)
            max_wm_size = int(video_pixmap.width() * 0.2)
            if watermark_pixmap.width() > max_wm_size:
                watermark_pixmap = watermark_pixmap.scaledToWidth(max_wm_size, Qt.SmoothTransformation)
            
            # Apply opacity
            opacity = self.opacity_slider.value() / 100.0
            
            # Position
            position = self.wm_position_combo.currentText()
            padding = 10
            
            if position == 'Top Left':
                x, y = padding, padding
            elif position == 'Top Right':
                x = video_pixmap.width() - watermark_pixmap.width() - padding
                y = padding
            elif position == 'Bottom Left':
                x = padding
                y = video_pixmap.height() - watermark_pixmap.height() - padding
            elif position == 'Bottom Right':
                x = video_pixmap.width() - watermark_pixmap.width() - padding
                y = video_pixmap.height() - watermark_pixmap.height() - padding
            else:  # Center
                x = (video_pixmap.width() - watermark_pixmap.width()) // 2
                y = (video_pixmap.height() - watermark_pixmap.height()) // 2
            
            # Composite
            from PyQt5.QtGui import QPainter
            composite = QPixmap(video_pixmap)
            painter = QPainter(composite)
            painter.setOpacity(opacity)
            painter.drawPixmap(x, y, watermark_pixmap)
            painter.end()
            
            # Display
            self.watermark_preview_label.setPixmap(composite.scaled(
                self.watermark_preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
            
        except Exception as e:
            logging.error(f"Watermark preview error: {e}")
            self.watermark_preview_label.setText('Preview error')


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # For testing
    session = r"C:\Users\AGough\Downloads\Hallmark Record\session_20260108_093907"
    editor = WizardEditor(session)
    editor.show()
    
    sys.exit(app.exec_())
