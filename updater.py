"""
Hallmark Record - Update Checker
Checks for updates from GitHub and notifies users
"""
import json
import urllib.request
import urllib.error
from packaging import version
import logging

# Configuration
CURRENT_VERSION = "1.0.6"
VERSION_URL = "https://raw.githubusercontent.com/agough77/hallmark-record/main/version.json"
RELEASES_URL = "https://github.com/agough77/hallmark-record/releases/latest"

class UpdateChecker:
    def __init__(self):
        self.current_version = CURRENT_VERSION
        self.latest_version = None
        self.update_info = None
        
    def check_for_updates(self, timeout=10):
        """
        Check if a new version is available
        Returns: (has_update, update_info_dict)
        """
        try:
            logging.info(f"Checking for updates (current version: {self.current_version})")
            
            # Try to use certifi for SSL certificates if available
            import ssl
            try:
                import certifi
                ssl_context = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ssl_context = ssl.create_default_context()
            
            # Fetch version.json from GitHub
            req = urllib.request.Request(
                VERSION_URL,
                headers={'User-Agent': 'HallmarkRecord/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                data = response.read().decode('utf-8')
                self.update_info = json.loads(data)
            
            self.latest_version = self.update_info.get('version', '0.0.0')
            
            # Compare versions
            has_update = version.parse(self.latest_version) > version.parse(self.current_version)
            
            if has_update:
                logging.info(f"Update available: {self.latest_version}")
            else:
                logging.info("Application is up to date")
            
            return has_update, self.update_info
            
        except urllib.error.URLError as e:
            logging.debug(f"Could not check for updates: {e}")
            return False, None
        except Exception as e:
            logging.debug(f"Update check error: {e}")
            return False, None
    
    def get_changelog(self):
        """Get the changelog from update info"""
        if self.update_info:
            return self.update_info.get('changelog', [])
        return []
    
    def is_critical_update(self):
        """Check if this is a critical update"""
        if self.update_info:
            return self.update_info.get('critical_update', False)
        return False
    
    def get_download_url(self):
        """Get the download URL"""
        if self.update_info:
            return self.update_info.get('download_url', RELEASES_URL)
        return RELEASES_URL
    
    def get_release_date(self):
        """Get the release date"""
        if self.update_info:
            return self.update_info.get('release_date', 'Unknown')
        return 'Unknown'

def get_current_version():
    """Get the current version"""
    return CURRENT_VERSION
