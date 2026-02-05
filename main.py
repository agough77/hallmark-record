"""
Hallmark Record - Multi-Input Recording & Editing Application
Main GUI application with recording and editing capabilities
"""
import sys
import os
import threading
import webbrowser
import psutil
import win32gui
import win32con
import win32process
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QListWidget, 
                            QGroupBox, QCheckBox, QMessageBox, QTextEdit,
                            QStatusBar, QProgressBar, QFileDialog, QLineEdit,
                            QMenuBar, QAction)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QIcon

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recorder.multi_input_recorder import MultiInputRecorder
from updater import UpdateChecker, get_current_version
from config_manager import get_config_manager


def activate_existing_instance():
    """Check if Recorder is already running and activate its window"""
    current_pid = os.getpid()
    
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            # Look for another instance of Hallmark Recorder
            if proc.info['name'] == 'Hallmark Recorder.exe' and proc.info['pid'] != current_pid:
                # Found another instance - activate its window
                def callback(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if pid == proc.info['pid']:
                            windows.append(hwnd)
                    return True
                
                windows = []
                win32gui.EnumWindows(callback, windows)
                
                if windows:
                    hwnd = windows[0]
                    # Restore if minimized
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    # Bring to foreground
                    win32gui.SetForegroundWindow(hwnd)
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            continue
    
    return False


class RecordingSignals(QObject):
    """Signals for thread-safe communication"""
    status_update = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    recording_started = pyqtSignal(str)
    recording_stopped = pyqtSignal()


class HallmarkRecordApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Load configuration
        self.config = get_config_manager()
        
        # Set output folder from config
        self.output_folder = self.config.get_output_folder()
        
        self.recorder = MultiInputRecorder(self.output_folder)
        self.signals = RecordingSignals()
        self.current_session = None
        self.selected_cameras = []
        self.selected_mics = []
        self.selected_monitors = []
        
        # Connect signals
        self.signals.status_update.connect(self.update_status)
        self.signals.error_occurred.connect(self.show_error)
        self.signals.recording_started.connect(self.on_recording_started)
        self.signals.recording_stopped.connect(self.on_recording_stopped)
        
        # Update checker
        self.update_checker = UpdateChecker()
        
        self.init_ui()
        self.load_devices()
        
        # Check for VLC on startup (after 1 second)
        QTimer.singleShot(1000, self.check_vlc_installation)
        
        # Check for updates on startup (after 2 seconds) if enabled
        if self.config.get('advanced.check_for_updates', True):
            QTimer.singleShot(2000, self.check_for_updates_silent)
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(f'Hallmark Record v{get_current_version()} - Multi-Input Recorder & Editor')
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel('🎥 Hallmark Record')
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        subtitle = QLabel('Record from multiple cameras, microphones, and screens simultaneously')
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet('color: #666; font-size: 14px;')
        main_layout.addWidget(subtitle)
        
        # Output folder selection
        folder_layout = QHBoxLayout()
        folder_label = QLabel('Save to:')
        folder_label.setStyleSheet('font-weight: bold; font-size: 12px;')
        folder_layout.addWidget(folder_label)
        
        self.folder_display = QLineEdit()
        self.folder_display.setText(self.output_folder)
        self.folder_display.setReadOnly(True)
        self.folder_display.setStyleSheet('''
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: #f5f5f5;
                font-size: 11px;
            }
        ''')
        folder_layout.addWidget(self.folder_display)
        
        browse_btn = QPushButton('📁 Browse...')
        browse_btn.setStyleSheet('''
            QPushButton {
                background: #2196F3;
                color: white;
                border: none;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #1976D2;
            }
        ''')
        browse_btn.clicked.connect(self.select_output_folder)
        folder_layout.addWidget(browse_btn)
        
        main_layout.addLayout(folder_layout)
        
        # btitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet('color: #666; font-size: 14px;')
        main_layout.addWidget(subtitle)
        
        # Device selection section
        devices_layout = QHBoxLayout()
        
        # Cameras
        cameras_group = self.create_device_group('Cameras', 'camera_list')
        devices_layout.addWidget(cameras_group)
        
        # Microphones
        mics_group = self.create_device_group('Microphones', 'mic_list')
        devices_layout.addWidget(mics_group)
        
        # Monitors
        monitors_group = self.create_device_group('Monitors/Screens', 'monitor_list')
        devices_layout.addWidget(monitors_group)
        
        main_layout.addLayout(devices_layout)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton('🔴 Start Recording')
        self.start_btn.setStyleSheet('''
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #5568d3, stop:1 #653a8b);
            }
            QPushButton:disabled {
                background: #cccccc;
            }
        ''')
        self.start_btn.clicked.connect(self.start_recording)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton('⏹️ Stop Recording')
        self.stop_btn.setStyleSheet('''
            QPushButton {
                background: #f44336;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #d32f2f;
            }
            QPushButton:disabled {
                background: #cccccc;
            }
        ''')
        self.stop_btn.clicked.connect(self.stop_recording)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        self.refresh_btn = QPushButton('🔄 Refresh Devices')
        self.refresh_btn.setStyleSheet('''
            QPushButton {
                background: #4caf50;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #45a049;
            }
        ''')
        self.refresh_btn.clicked.connect(self.load_devices)
        control_layout.addWidget(self.refresh_btn)
        
        self.edit_btn = QPushButton('✂️ Open Editor')
        self.edit_btn.setStyleSheet('''
            QPushButton {
                background: #ff9800;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #f57c00;
            }
        ''')
        self.edit_btn.clicked.connect(self.open_editor)
        control_layout.addWidget(self.edit_btn)
        
        main_layout.addLayout(control_layout)
        
        # Log area
        log_group = QGroupBox('Recording Log')
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('Ready')
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
    def create_device_group(self, title, list_name):
        """Create a device selection group"""
        group = QGroupBox(title)
        layout = QVBoxLayout()
        
        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.MultiSelection)
        setattr(self, list_name, list_widget)
        layout.addWidget(list_widget)
        
        select_all_btn = QPushButton(f'Select All {title}')
        select_all_btn.clicked.connect(lambda: self.select_all_devices(list_name))
        layout.addWidget(select_all_btn)
        
        group.setLayout(layout)
        return group
    
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # Help menu
        help_menu = menubar.addMenu('&Help')
        
        # Check for updates action
        update_action = QAction('Check for &Updates', self)
        update_action.setStatusTip('Check if a new version is available')
        update_action.triggered.connect(self.check_for_updates_manual)
        help_menu.addAction(update_action)
        
        help_menu.addSeparator()
        
        # About action
        about_action = QAction('&About', self)
        about_action.setStatusTip('About Hallmark Record')
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def select_all_devices(self, list_name):
        """Select all devices in a list"""
        list_widget = getattr(self, list_name)
        for i in range(list_widget.count()):
            list_widget.item(i).setSelected(True)
    
    def load_devices(self):
        """Load all available devices"""
        self.log('Loading devices...')
        
        try:
            # Load cameras
            cameras = self.recorder.list_video_devices()
            self.camera_list.clear()
            for camera in cameras:
                self.camera_list.addItem(camera)
            self.log(f'Found {len(cameras)} camera(s)')
            
            # Load microphones
            mics = self.recorder.list_audio_devices()
            self.mic_list.clear()
            for mic in mics:
                self.mic_list.addItem(mic)
            self.log(f'Found {len(mics)} microphone(s)')
            
            # Load monitors
            monitors = self.recorder.list_monitors()
            self.monitor_list.clear()
            self.monitors_data = monitors
            for idx, monitor in enumerate(monitors):
                display_name = f"{monitor['name']} - {monitor['width']}x{monitor['height']}"
                if monitor['is_primary']:
                    display_name += ' (Primary)'
                self.monitor_list.addItem(display_name)
            self.log(f'Found {len(monitors)} monitor(s)')
            
            self.status_bar.showMessage('Devices loaded successfully')
            
        except Exception as e:
            self.log(f'Error loading devices: {str(e)}')
            self.show_error(f'Error loading devices: {str(e)}')
    
    def start_recording(self):
        """Start recording from selected devices"""
        # Get selected devices
        selected_cameras = [item.text() for item in self.camera_list.selectedItems()]
        selected_mics = [item.text() for item in self.mic_list.selectedItems()]
        selected_monitor_indices = [self.monitor_list.row(item) for item in self.monitor_list.selectedItems()]
        selected_monitors = [self.monitors_data[i] for i in selected_monitor_indices]
        
        if not selected_cameras and not selected_mics and not selected_monitors:
            QMessageBox.warning(self, 'No Devices Selected', 
                              'Please select at least one device to record from.')
            return
        
        self.log('Starting recording...')
        self.log(f'Cameras: {len(selected_cameras)}, Mics: {len(selected_mics)}, Monitors: {len(selected_monitors)}')
        
        try:
            session_dir = self.recorder.start_recording(
                cameras=selected_cameras if selected_cameras else None,
                microphones=selected_mics if selected_mics else None,
                monitors=selected_monitors if selected_monitors else None
            )
            
            self.current_session = session_dir
            self.log(f'Recording started! Session: {os.path.basename(session_dir)}')
            self.status_bar.showMessage('🔴 Recording...')
            
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.refresh_btn.setEnabled(False)
            
        except Exception as e:
            self.log(f'Error starting recording: {str(e)}')
            self.show_error(f'Error starting recording: {str(e)}')
    
    def stop_recording(self):
        """Stop all recordings"""
        self.log('Stopping recording...')
        
        try:
            self.recorder.stop_recording()
            self.log('Recording stopped successfully')
            self.log(f'Files saved to: {self.current_session}')
            self.status_bar.showMessage('Recording stopped')
            
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.refresh_btn.setEnabled(True)
            
            # Show success message
            QMessageBox.information(self, 'Recording Complete',
                                  f'Recording saved to:\n{self.current_session}\n\nClick "Open Editor" to edit your recordings.')
            
        except Exception as e:
            self.log(f'Error stopping recording: {str(e)}')
            self.show_error(f'Error stopping recording: {str(e)}')
    
    def open_editor(self):
        """Open the wizard-style video editor"""
        self.log('Opening video editor...')
        
        try:
            from editor.wizard_editor import WizardEditor
            
            # Always show session selector dialog - let user choose which session to edit
            session_folder = self.show_session_selector()
            
            if session_folder:
                # Find FFmpeg path
                ffmpeg_path = self.find_ffmpeg()
                
                # Create and show wizard editor
                self.editor_window = WizardEditor(session_folder, ffmpeg_path)
                self.editor_window.show()
                
                self.log(f'Editor opened for session: {os.path.basename(session_folder)}')
            else:
                self.log('Editor opening cancelled')
            
        except Exception as e:
            self.log(f'Error opening editor: {str(e)}')
            self.show_error(f'Error opening editor: {str(e)}')
    
    def show_session_selector(self):
        """Show dialog to select, view info, and manage recording sessions"""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem, QHeaderView
        import shutil
        
        dialog = QDialog(self)
        dialog.setWindowTitle('Select Recording Session')
        dialog.setMinimumWidth(900)
        dialog.setMinimumHeight(600)
        
        layout = QVBoxLayout(dialog)
        
        # Current session indicator
        if self.current_session:
            current_info = QLabel(f'📍 Current Session: {os.path.basename(self.current_session)}')
            current_info.setStyleSheet('font-size: 14px; color: #2196F3; padding: 10px; font-weight: bold; background: #E3F2FD; border-radius: 5px;')
            layout.addWidget(current_info)
        
        # Instructions
        info = QLabel('Select recording sessions to edit or delete (hold Ctrl to select multiple):')
        info.setStyleSheet('font-size: 13px; color: #666; padding: 10px; font-weight: bold;')
        layout.addWidget(info)
        
        # Session table
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(['Date & Time', 'Session Name', 'Files', 'Size', 'Location'])
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.MultiSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Load sessions from output folder
        sessions = []
        if os.path.exists(self.output_folder):
            for item in os.listdir(self.output_folder):
                session_path = os.path.join(self.output_folder, item)
                if os.path.isdir(session_path) and item.startswith('session_'):
                    try:
                        # Get session info
                        files = os.listdir(session_path)
                        file_count = len(files)
                        
                        # Calculate total size
                        total_size = 0
                        for f in files:
                            file_path = os.path.join(session_path, f)
                            if os.path.isfile(file_path):
                                total_size += os.path.getsize(file_path)
                        
                        size_mb = total_size / (1024 * 1024)
                        
                        # Get creation time from folder name
                        date_display = 'Unknown'
                        date_obj = None
                        
                        try:
                            # Extract date string: session_20260205_092729 -> 20260205_092729
                            date_str = item.replace('session_', '')
                            # Parse: 20260205_092729
                            date_obj = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                            date_display = date_obj.strftime('%b %d, %Y at %I:%M:%S %p')
                        except Exception as e:
                            # If parsing fails, try to use file modification time
                            try:
                                mtime = os.path.getmtime(session_path)
                                date_obj = datetime.fromtimestamp(mtime)
                                date_display = date_obj.strftime('%b %d, %Y at %I:%M:%S %p')
                            except:
                                date_display = 'Unknown'
                        
                        sessions.append({
                            'name': item,
                            'path': session_path,
                            'date': date_display,
                            'date_obj': date_obj,
                            'files': file_count,
                            'size': size_mb
                        })
                    except Exception as e:
                        continue
        
        # Sort by date (newest first)
        sessions.sort(key=lambda x: x['name'], reverse=True)
        
        # Populate table
        table.setRowCount(len(sessions))
        for row, session in enumerate(sessions):
            # Check if this is the current session
            is_current = self.current_session and os.path.normpath(session['path']) == os.path.normpath(self.current_session)
            
            date_item = QTableWidgetItem(session['date'])
            name_item = QTableWidgetItem(session['name'])
            files_item = QTableWidgetItem(str(session['files']))
            size_item = QTableWidgetItem(f"{session['size']:.2f} MB")
            path_item = QTableWidgetItem(session['path'])
            
            # Highlight current session
            if is_current:
                from PyQt5.QtGui import QColor, QBrush
                highlight_color = QColor(227, 242, 253)  # Light blue
                date_item.setBackground(QBrush(highlight_color))
                name_item.setBackground(QBrush(highlight_color))
                files_item.setBackground(QBrush(highlight_color))
                size_item.setBackground(QBrush(highlight_color))
                path_item.setBackground(QBrush(highlight_color))
                
                # Add indicator to name
                name_item.setText(f"📍 {session['name']}")
            
            table.setItem(row, 0, date_item)
            table.setItem(row, 1, name_item)
            table.setItem(row, 2, files_item)
            table.setItem(row, 3, size_item)
            table.setItem(row, 4, path_item)
        
        # Auto-resize columns
        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        # Auto-select current session if it exists
        if self.current_session:
            for row, session in enumerate(sessions):
                if os.path.normpath(session['path']) == os.path.normpath(self.current_session):
                    table.selectRow(row)
                    break
        
        # Double-click to open session
        def on_double_click(item):
            if item:
                table.selectRow(item.row())
                dialog.accept()
        table.itemDoubleClicked.connect(on_double_click)
        
        layout.addWidget(table)
        
        # Storage info
        if sessions:
            total_size = sum(s['size'] for s in sessions)
            storage_info = QLabel(f'Total storage used: {total_size:.2f} MB across {len(sessions)} sessions')
            storage_info.setStyleSheet('font-size: 11px; color: #999; padding: 5px;')
            layout.addWidget(storage_info)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        delete_btn = QPushButton('🗑️ Delete Selected')
        delete_btn.setStyleSheet('background: #f44336; color: white; padding: 8px 15px; font-weight: bold;')
        delete_btn.clicked.connect(lambda: self.delete_session_from_table(table, sessions, storage_info if sessions else None))
        button_layout.addWidget(delete_btn)
        
        button_layout.addStretch()
        
        button_box = QDialogButtonBox(QDialogButtonBox.Open | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
        
        # Show dialog
        selected_session = None
        if dialog.exec_() == QDialog.Accepted:
            selected_rows = table.selectionModel().selectedRows()
            if len(selected_rows) == 1:
                row = selected_rows[0].row()
                if row < len(sessions):
                    selected_session = sessions[row]['path']
            elif len(selected_rows) > 1:
                QMessageBox.warning(self, 'Multiple Selection', 'Please select only one session to open.')
        
        return selected_session
    
    def delete_session_from_table(self, table, sessions, storage_info):
        """Delete selected sessions from table"""
        import shutil
        
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, 'No Selection', 'Please select one or more sessions to delete.')
            return
        
        # Get selected sessions
        selected_sessions = []
        for index in selected_rows:
            row = index.row()
            if row < len(sessions):
                selected_sessions.append((row, sessions[row]))
        
        # Sort by row in reverse order so we can delete from bottom up
        selected_sessions.sort(key=lambda x: x[0], reverse=True)
        
        # Build confirmation message
        if len(selected_sessions) == 1:
            session = selected_sessions[0][1]
            message = (
                f"Are you sure you want to delete this session?\n\n"
                f"Session: {session['name']}\n"
                f"Date: {session['date']}\n"
                f"Files: {session['files']}\n"
                f"Size: {session['size']:.2f} MB\n\n"
                f"This action cannot be undone!"
            )
        else:
            total_size = sum(s[1]['size'] for s in selected_sessions)
            total_files = sum(s[1]['files'] for s in selected_sessions)
            message = (
                f"Are you sure you want to delete {len(selected_sessions)} sessions?\n\n"
                f"Total Files: {total_files}\n"
                f"Total Size: {total_size:.2f} MB\n\n"
                f"This action cannot be undone!"
            )
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            'Confirm Deletion',
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            deleted_count = 0
            failed_count = 0
            
            for row, session in selected_sessions:
                try:
                    # Delete the session folder
                    shutil.rmtree(session['path'])
                    
                    # Remove from table and sessions list
                    table.removeRow(row)
                    sessions.pop(row)
                    
                    deleted_count += 1
                    self.log(f"Deleted session: {session['name']}")
                    
                except Exception as e:
                    failed_count += 1
                    self.log(f"Error deleting session {session['name']}: {str(e)}")
            
            # Update storage info
            if storage_info:
                if sessions:
                    total_size = sum(s['size'] for s in sessions)
                    storage_info.setText(f'Total storage used: {total_size:.2f} MB across {len(sessions)} sessions')
                else:
                    storage_info.setText('No sessions found')
            
            # Show result
            if failed_count == 0:
                QMessageBox.information(self, 'Deleted', f"Successfully deleted {deleted_count} session(s).")
            else:
                QMessageBox.warning(self, 'Partial Success', 
                    f"Deleted {deleted_count} session(s).\nFailed to delete {failed_count} session(s).")
    
    def find_ffmpeg(self):
        """Find ffmpeg executable"""
        # Determine the base path (works for both script and PyInstaller bundle)
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle
            base_path = sys._MEIPASS
        else:
            # Running as script
            base_path = os.path.dirname(os.path.abspath(__file__))
        
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
    
    def start_editor_server(self):
        """Start the Flask editor server (DEPRECATED - now using desktop wizard)"""
        try:
            from editor.video_editor import app
            app.run(debug=False, port=5500, use_reloader=False)
        except Exception as e:
            self.signals.error_occurred.emit(f'Error starting editor server: {str(e)}')
    
    def log(self, message):
        """Add message to log"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f'[{timestamp}] {message}')
    
    def update_status(self, message):
        """Update status bar"""
        self.status_bar.showMessage(message)
    
    def show_error(self, message):
        """Show error dialog"""
        QMessageBox.critical(self, 'Error', message)
    
    def select_output_folder(self):
        """Let user select where to save recordings"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Save Recordings",
            self.output_folder,
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.output_folder = folder
            self.folder_display.setText(folder)
            
            # Update recorder with new output directory
            self.recorder = MultiInputRecorder(self.output_folder)
            
            # Save to config
            self.config.set('installation.output_folder', folder)
            
            self.log_text.append(f"📁 Output folder changed to: {folder}")
            self.status_bar.showMessage(f"Saving to: {folder}")
    
    def on_recording_started(self, session_dir):
        """Handle recording started"""
        self.current_session = session_dir
        
    def on_recording_stopped(self):
        """Handle recording stopped"""
        pass
    
    def check_vlc_installation(self):
        """Check if VLC is installed and prompt to install if missing"""
        from vlc_installer import check_vlc_installed, install_vlc
        from PyQt5.QtCore import QThread, pyqtSignal
        from PyQt5.QtWidgets import QProgressDialog
        
        # Check if VLC is installed
        installed, path = check_vlc_installed()
        
        if installed:
            # VLC is already installed
            return
        
        # VLC not found - prompt user to install
        reply = QMessageBox.question(
            self,
            'VLC Media Player Not Found',
            'VLC Media Player is required for live video preview in the editor.\n\n'
            'Would you like to install VLC now? (~40 MB download)\n\n'
            'You can skip this and install it later from the editor.',
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
        progress.setCancelButton(None)  # Don't allow canceling
        progress.show()
        
        # Install in background thread
        class InstallThread(QThread):
            finished_signal = pyqtSignal(bool, str)
            
            def run(self):
                try:
                    success, message = install_vlc()
                    self.finished_signal.emit(success, message)
                except Exception as e:
                    self.finished_signal.emit(False, str(e))
        
        def on_install_complete(success, message):
            progress.close()
            
            # Clean up thread
            if hasattr(self, 'vlc_install_thread'):
                self.vlc_install_thread.wait()
                self.vlc_install_thread.deleteLater()
                self.vlc_install_thread = None
            
            if success:
                QMessageBox.information(
                    self,
                    'Installation Complete',
                    f'VLC Media Player has been installed successfully!\n\n'
                    f'{message}\n\n'
                    'Live video preview is now available in the editor.'
                )
            else:
                QMessageBox.warning(
                    self,
                    'Installation Failed',
                    f'Failed to install VLC:\n\n{message}\n\n'
                    'You can install VLC manually from:\nhttps://www.videolan.org/vlc/\n\n'
                    'The application will work, but live video preview will be unavailable.'
                )
        
        self.vlc_install_thread = InstallThread()
        self.vlc_install_thread.finished_signal.connect(on_install_complete)
        self.vlc_install_thread.start()
    
    def check_for_updates_silent(self):
        """Check for updates silently on startup"""
        def check():
            try:
                has_update, info = self.update_checker.check_for_updates()
                if has_update:
                    # Show notification in status bar using QTimer to ensure it's in main thread
                    version = info.get('version', 'Unknown')
                    QTimer.singleShot(0, lambda: self.status_bar.showMessage(
                        f'⚠️ Update available: v{version} - Click Help > Check for Updates', 15000
                    ))
            except Exception as e:
                # Silently fail - don't bother user if update check fails
                pass
        
        # Run in background thread
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
    
    def check_for_updates_manual(self):
        """Check for updates when user clicks menu"""
        self.status_bar.showMessage('Checking for updates...')
        
        def check():
            has_update, info = self.update_checker.check_for_updates()
            
            # Update UI in main thread
            QTimer.singleShot(0, lambda: self.show_update_result(has_update, info))
        
        # Run in background thread
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
    
    def show_update_result(self, has_update, info):
        """Show update check result to user"""
        self.status_bar.showMessage('Ready')
        
        if has_update:
            version = info.get('version', 'Unknown')
            release_date = info.get('release_date', 'Unknown')
            changelog = info.get('changelog', [])
            is_critical = info.get('critical_update', False)
            
            # Create message
            msg = f"<h3>Update Available: v{version}</h3>"
            msg += f"<p><b>Released:</b> {release_date}</p>"
            
            if is_critical:
                msg += "<p><b style='color: red;'>⚠️ This is a critical update!</b></p>"
            
            if changelog:
                msg += "<p><b>What's new:</b></p><ul>"
                for item in changelog:
                    msg += f"<li>{item}</li>"
                msg += "</ul>"
            
            msg += "<p>Would you like to download it now?</p>"
            
            # Show dialog
            reply = QMessageBox.question(
                self,
                'Update Available',
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes if is_critical else QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Open releases page in browser
                download_url = info.get('download_url', 'https://github.com/agough77/hallmark-record/releases/latest')
                webbrowser.open(download_url)
                
                QMessageBox.information(
                    self,
                    'Download Started',
                    'The download page has been opened in your browser.\\n\\n'
                    'Please download and install the update, then restart the application.'
                )
        
        elif info is None:
            # Could not check for updates
            QMessageBox.warning(
                self,
                'Update Check Failed',
                'Could not check for updates. Please check your internet connection and try again.\\n\\n'
                'You can also visit:\\n'
                'https://github.com/agough77/hallmark-record/releases'
            )
        else:
            # Up to date
            QMessageBox.information(
                self,
                'No Updates Available',
                f'You are running the latest version (v{get_current_version()}).'
            )
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            'About Hallmark Record',
            f'<h2>Hallmark Record</h2>'
            f'<p><b>Version:</b> {get_current_version()}</p>'
            f'<p>Multi-input recording and editing application</p>'
            f'<p>Record from multiple cameras, microphones, and screens simultaneously.</p>'
            f'<p><br></p>'
            f'<p>For updates and support, visit:<br>'
            f'<a href="https://github.com/agough77/hallmark-record">github.com/agough77/hallmark-record</a></p>'
        )


def main():
    # Check if another instance is already running
    if activate_existing_instance():
        # Found and activated existing instance, exit this one
        return
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = HallmarkRecordApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
