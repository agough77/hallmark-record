"""
VLC Media Player Installer Utility
Automatically downloads and installs VLC if not present
"""
import os
import sys
import subprocess
import urllib.request
import tempfile
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)

def check_vlc_installed():
    """Check if VLC is installed on the system"""
    if sys.platform == 'win32':
        # Check common VLC installation paths on Windows
        vlc_paths = [
            r"C:\Program Files\VideoLAN\VLC",
            r"C:\Program Files (x86)\VideoLAN\VLC",
            os.path.expandvars(r"%PROGRAMFILES%\VideoLAN\VLC"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\VideoLAN\VLC"),
        ]
        
        for path in vlc_paths:
            if os.path.exists(path):
                vlc_dll = os.path.join(path, "libvlc.dll")
                if os.path.exists(vlc_dll):
                    logging.info(f'VLC found at: {path}')
                    return True, path
        
        # Try to find via PATH
        try:
            result = subprocess.run(['where', 'vlc'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                vlc_path = result.stdout.strip().split('\n')[0]
                if vlc_path:
                    logging.info(f'VLC found in PATH: {vlc_path}')
                    return True, os.path.dirname(vlc_path)
        except:
            pass
        
        return False, None
    
    elif sys.platform == 'darwin':  # macOS
        vlc_path = '/Applications/VLC.app'
        if os.path.exists(vlc_path):
            return True, vlc_path
        return False, None
    
    else:  # Linux
        try:
            result = subprocess.run(['which', 'vlc'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return True, result.stdout.strip()
        except:
            pass
        return False, None


def install_vlc_windows():
    """Install VLC on Windows using winget or direct download"""
    logging.info('Attempting to install VLC on Windows...')
    
    # Try winget first (Windows Package Manager)
    try:
        logging.info('Trying winget installation...')
        result = subprocess.run(
            ['winget', 'install', '--id=VideoLAN.VLC', '--silent', '--accept-package-agreements', '--accept-source-agreements'],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            logging.info('VLC installed successfully via winget')
            return True, 'Installed via Windows Package Manager'
        else:
            logging.warning(f'winget failed: {result.stderr}')
    except Exception as e:
        logging.warning(f'winget not available: {str(e)}')
    
    # Try chocolatey
    try:
        logging.info('Trying chocolatey installation...')
        result = subprocess.run(
            ['choco', 'install', 'vlc', '-y'],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            logging.info('VLC installed successfully via chocolatey')
            return True, 'Installed via Chocolatey'
    except Exception as e:
        logging.warning(f'chocolatey not available: {str(e)}')
    
    # Direct download and install
    try:
        logging.info('Downloading VLC installer...')
        # Use the official VLC download URL (64-bit)
        vlc_url = 'https://get.videolan.org/vlc/last/win64/vlc-3.0.20-win64.exe'
        
        # Download to temp directory
        temp_dir = tempfile.gettempdir()
        installer_path = os.path.join(temp_dir, 'vlc_installer.exe')
        
        urllib.request.urlretrieve(vlc_url, installer_path)
        logging.info(f'Downloaded VLC installer to: {installer_path}')
        
        # Run installer silently
        logging.info('Running VLC installer...')
        result = subprocess.run(
            [installer_path, '/S'],  # /S for silent install
            timeout=300
        )
        
        # Clean up
        try:
            os.remove(installer_path)
        except:
            pass
        
        if result.returncode == 0:
            logging.info('VLC installed successfully')
            return True, 'Installed from official VLC website'
        else:
            return False, f'Installer returned code: {result.returncode}'
    
    except Exception as e:
        logging.error(f'Direct installation failed: {str(e)}')
        return False, str(e)


def install_vlc_macos():
    """Install VLC on macOS using Homebrew"""
    try:
        logging.info('Installing VLC via Homebrew...')
        result = subprocess.run(
            ['brew', 'install', '--cask', 'vlc'],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            return True, 'Installed via Homebrew'
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)


def install_vlc_linux():
    """Install VLC on Linux using apt or dnf"""
    try:
        # Try apt (Debian/Ubuntu)
        logging.info('Trying apt installation...')
        result = subprocess.run(
            ['sudo', 'apt-get', 'install', '-y', 'vlc'],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            return True, 'Installed via apt-get'
    except Exception as e:
        logging.warning(f'apt failed: {str(e)}')
    
    try:
        # Try dnf (Fedora/RHEL)
        logging.info('Trying dnf installation...')
        result = subprocess.run(
            ['sudo', 'dnf', 'install', '-y', 'vlc'],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            return True, 'Installed via dnf'
    except Exception as e:
        logging.warning(f'dnf failed: {str(e)}')
    
    return False, 'Could not install VLC. Please install manually.'


def install_vlc():
    """Install VLC based on the current platform"""
    if sys.platform == 'win32':
        return install_vlc_windows()
    elif sys.platform == 'darwin':
        return install_vlc_macos()
    else:
        return install_vlc_linux()


if __name__ == '__main__':
    installed, path = check_vlc_installed()
    if installed:
        print(f'VLC is already installed at: {path}')
    else:
        print('VLC is not installed. Installing...')
        success, message = install_vlc()
        if success:
            print(f'Success! {message}')
        else:
            print(f'Failed to install VLC: {message}')
