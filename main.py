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
        
        # Set default output folder
        self.output_folder = os.path.join(os.path.expanduser("~"), "Downloads", "Hallmark Record")
        
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
        
        # Check for updates on startup (after 2 seconds)
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
        """Open the web-based video editor"""
        self.log('Opening video editor...')
        
        try:
            # Start Flask server in a thread
            editor_thread = threading.Thread(target=self.start_editor_server, daemon=True)
            editor_thread.start()
            
            # Wait a moment for server to start
            QTimer.singleShot(2000, lambda: webbrowser.open('http://localhost:5500'))
            
            self.log('Editor opened in browser at http://localhost:5500')
            
        except Exception as e:
            self.log(f'Error opening editor: {str(e)}')
            self.show_error(f'Error opening editor: {str(e)}')
    
    def start_editor_server(self):
        """Start the Flask editor server"""
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
            
            self.log_text.append(f"📁 Output folder changed to: {folder}")
            self.status_bar.showMessage(f"Saving to: {folder}")
    
    def on_recording_started(self, session_dir):
        """Handle recording started"""
        self.current_session = session_dir
        
    def on_recording_stopped(self):
        """Handle recording stopped"""
        pass
    
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
