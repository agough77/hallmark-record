"""
Unattended Installer for Hallmark Record
Allows silent installation with pre-configured settings
"""
import os
import sys
import json
import argparse
import shutil
from pathlib import Path


def create_unattended_config():
    """Create an unattended installation configuration file"""
    
    config = {
        "installation": {
            "silent": True,
            "install_path": "C:\\Program Files\\Hallmark Record",
            "output_folder": "D:\\HallmarkRecordings",
            "create_desktop_shortcut": True,
            "create_start_menu_shortcut": True,
            "auto_start": False
        },
        "recording": {
            "default_quality": "high",
            "auto_name_sessions": True
        },
        "export": {
            "default_quality": "medium",
            "auto_export_after_recording": False
        },
        "watermark": {
            "enabled": True,
            "image_path": "C:\\Company\\logo.png",
            "position": "top_right",
            "opacity": 0.7
        },
        "upload": {
            "enabled": True,
            "auto_upload_after_export": True,
            "destinations": [
                {
                    "name": "Company SharePoint",
                    "type": "sharepoint",
                    "url": "https://company.sharepoint.com/sites/videos",
                    "username": "",
                    "password_encrypted": "",
                    "enabled": True
                }
            ]
        },
        "advanced": {
            "enable_logging": True,
            "check_for_updates": True
        }
    }
    
    output_path = "unattended_config.json"
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Unattended configuration created: {output_path}")
    print("\nEdit this file with your organization's settings, then use:")
    print(f"  Setup.exe /SILENT /CONFIG={output_path}")
    print("\nOr for completely silent install:")
    print(f"  Setup.exe /VERYSILENT /CONFIG={output_path}")
    
    return output_path


def install_with_config(config_file, install_dir=None):
    """Perform installation using configuration file"""
    
    if not os.path.exists(config_file):
        print(f"Error: Configuration file not found: {config_file}")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error reading configuration: {e}")
        return False
    
    # Get installation settings
    installation = config.get('installation', {})
    
    if install_dir is None:
        install_dir = installation.get('install_path', 'C:\\Program Files\\Hallmark Record')
    
    output_folder = installation.get('output_folder', 'C:\\HallmarkRecordings')
    
    print(f"Installing Hallmark Record...")
    print(f"  Installation directory: {install_dir}")
    print(f"  Recording output folder: {output_folder}")
    
    # Create directories
    try:
        os.makedirs(install_dir, exist_ok=True)
        os.makedirs(output_folder, exist_ok=True)
        print(f"  ✓ Directories created")
    except Exception as e:
        print(f"  ✗ Error creating directories: {e}")
        return False
    
    # Copy configuration to AppData
    try:
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        config_dir = os.path.join(appdata, 'Hallmark Record')
        os.makedirs(config_dir, exist_ok=True)
        
        user_config_path = os.path.join(config_dir, 'config.json')
        
        # Prepare user config (remove installation-specific settings)
        user_config = config.copy()
        if 'installation' in user_config:
            # Keep only necessary settings
            user_config['installation'] = {
                'output_folder': output_folder
            }
        
        with open(user_config_path, 'w') as f:
            json.dump(user_config, f, indent=2)
        
        print(f"  ✓ Configuration saved to: {user_config_path}")
    except Exception as e:
        print(f"  ✗ Error saving configuration: {e}")
        return False
    
    # Create shortcuts if requested
    if installation.get('create_desktop_shortcut', True):
        try:
            create_desktop_shortcut(install_dir)
            print(f"  ✓ Desktop shortcut created")
        except Exception as e:
            print(f"  ✗ Error creating desktop shortcut: {e}")
    
    if installation.get('create_start_menu_shortcut', True):
        try:
            create_start_menu_shortcut(install_dir)
            print(f"  ✓ Start menu shortcut created")
        except Exception as e:
            print(f"  ✗ Error creating start menu shortcut: {e}")
    
    print("\n✓ Installation complete!")
    return True


def create_desktop_shortcut(install_dir):
    """Create desktop shortcut"""
    try:
        from win32com.client import Dispatch
        
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        shortcut_path = os.path.join(desktop, 'Hallmark Record.lnk')
        
        target = os.path.join(install_dir, 'Hallmark Recorder.exe')
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = install_dir
        shortcut.IconLocation = target
        shortcut.save()
        
        return True
    except:
        # Fallback: Create simple batch file
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        bat_path = os.path.join(desktop, 'Hallmark Record.bat')
        
        with open(bat_path, 'w') as f:
            f.write(f'@echo off\n')
            f.write(f'cd /d "{install_dir}"\n')
            f.write(f'start "" "Hallmark Recorder.exe"\n')
        
        return True


def create_start_menu_shortcut(install_dir):
    """Create start menu shortcut"""
    try:
        from win32com.client import Dispatch
        
        start_menu = os.path.join(
            os.environ.get('APPDATA', os.path.expanduser('~')),
            'Microsoft', 'Windows', 'Start Menu', 'Programs'
        )
        
        hallmark_folder = os.path.join(start_menu, 'Hallmark Record')
        os.makedirs(hallmark_folder, exist_ok=True)
        
        # Create recorder shortcut
        shortcut_path = os.path.join(hallmark_folder, 'Hallmark Recorder.lnk')
        target = os.path.join(install_dir, 'Hallmark Recorder.exe')
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = install_dir
        shortcut.IconLocation = target
        shortcut.save()
        
        # Create editor shortcut
        editor_shortcut_path = os.path.join(hallmark_folder, 'Hallmark Editor.lnk')
        editor_target = os.path.join(install_dir, 'Hallmark Editor.exe')
        
        if os.path.exists(editor_target):
            editor_shortcut = shell.CreateShortCut(editor_shortcut_path)
            editor_shortcut.Targetpath = editor_target
            editor_shortcut.WorkingDirectory = install_dir
            editor_shortcut.IconLocation = editor_target
            editor_shortcut.save()
        
        return True
    except Exception as e:
        print(f"Warning: Could not create start menu shortcuts: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Hallmark Record Unattended Installer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Create configuration template
  python unattended_installer.py --create-config
  
  # Install with configuration
  python unattended_installer.py --config unattended_config.json
  
  # Install with configuration and custom directory
  python unattended_installer.py --config unattended_config.json --install-dir "D:\\Apps\\HallmarkRecord"
  
  # For Inno Setup silent install
  Setup.exe /VERYSILENT /CONFIG=unattended_config.json
        '''
    )
    
    parser.add_argument(
        '--create-config',
        action='store_true',
        help='Create an unattended configuration template'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file for installation'
    )
    
    parser.add_argument(
        '--install-dir',
        type=str,
        help='Custom installation directory'
    )
    
    args = parser.parse_args()
    
    if args.create_config:
        create_unattended_config()
        return 0
    
    if args.config:
        success = install_with_config(args.config, args.install_dir)
        return 0 if success else 1
    
    # No arguments - show help
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
