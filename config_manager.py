"""
Configuration Manager for Hallmark Record
Handles loading and saving application configuration
"""
import json
import os
from pathlib import Path


class ConfigManager:
    """Manages application configuration"""
    
    DEFAULT_CONFIG = {
        "version": "1.0",
        "installation": {
            "output_folder": "",  # Will be set to user's Downloads folder
            "install_path": "",
            "create_desktop_shortcut": True,
            "create_start_menu_shortcut": True,
            "auto_start": False
        },
        "recording": {
            "default_quality": "high",
            "auto_name_sessions": True,
            "session_name_format": "session_%Y%m%d_%H%M%S"
        },
        "export": {
            "default_quality": "medium",
            "auto_export_after_recording": False,
            "export_format": "mp4"
        },
        "watermark": {
            "enabled": False,
            "image_path": "",
            "position": "top_right",
            "opacity": 0.7
        },
        "upload": {
            "enabled": False,
            "auto_upload_after_export": False,
            "destinations": []
        },
        "advanced": {
            "ffmpeg_path": "",
            "enable_logging": True,
            "log_level": "INFO",
            "check_for_updates": True
        }
    }
    
    def __init__(self, config_path=None):
        """Initialize configuration manager"""
        if config_path is None:
            # Use AppData folder for user config
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            config_dir = os.path.join(appdata, 'Hallmark Record')
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, 'config.json')
        
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return self.merge_with_defaults(config)
            except Exception as e:
                print(f"Error loading config: {e}")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Create default config
            config = self.DEFAULT_CONFIG.copy()
            # Set output folder to Downloads by default
            config['installation']['output_folder'] = os.path.join(
                os.path.expanduser("~"), "Downloads", "Hallmark Record"
            )
            self.save_config(config)
            return config
    
    def merge_with_defaults(self, config):
        """Merge loaded config with defaults to ensure all keys exist"""
        def merge_dict(base, update):
            result = base.copy()
            for key, value in update.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dict(result[key], value)
                else:
                    result[key] = value
            return result
        
        return merge_dict(self.DEFAULT_CONFIG.copy(), config)
    
    def save_config(self, config=None):
        """Save configuration to file"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get(self, key_path, default=None):
        """Get configuration value by dot-notation path
        
        Example: get('installation.output_folder')
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path, value):
        """Set configuration value by dot-notation path"""
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        self.save_config()
    
    def get_output_folder(self):
        """Get configured output folder"""
        folder = self.get('installation.output_folder')
        if not folder:
            folder = os.path.join(os.path.expanduser("~"), "Downloads", "Hallmark Record")
            self.set('installation.output_folder', folder)
        
        # Ensure folder exists
        os.makedirs(folder, exist_ok=True)
        return folder
    
    def get_watermark_config(self):
        """Get watermark configuration"""
        return {
            'enabled': self.get('watermark.enabled', False),
            'image_path': self.get('watermark.image_path', ''),
            'position': self.get('watermark.position', 'top_right'),
            'opacity': self.get('watermark.opacity', 0.7)
        }
    
    def get_upload_destinations(self):
        """Get enabled upload destinations"""
        destinations = self.get('upload.destinations', [])
        return [d for d in destinations if d.get('enabled', False)]
    
    def add_upload_destination(self, destination):
        """Add a new upload destination"""
        destinations = self.get('upload.destinations', [])
        destinations.append(destination)
        self.set('upload.destinations', destinations)
    
    def get_export_settings(self):
        """Get export settings"""
        return {
            'quality': self.get('export.default_quality', 'medium'),
            'format': self.get('export.export_format', 'mp4'),
            'auto_export': self.get('export.auto_export_after_recording', False)
        }
    
    def export_config(self, output_path):
        """Export configuration to a file for deployment"""
        try:
            with open(output_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting config: {e}")
            return False
    
    def import_config(self, input_path):
        """Import configuration from a file"""
        try:
            with open(input_path, 'r') as f:
                imported_config = json.load(f)
            
            # Merge with current config
            self.config = self.merge_with_defaults(imported_config)
            self.save_config()
            return True
        except Exception as e:
            print(f"Error importing config: {e}")
            return False


# Global config instance
_config_manager = None

def get_config_manager():
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


if __name__ == '__main__':
    # Test configuration manager
    config = ConfigManager()
    
    print("Output folder:", config.get_output_folder())
    print("Watermark config:", config.get_watermark_config())
    print("Export settings:", config.get_export_settings())
    
    # Test setting values
    config.set('watermark.enabled', True)
    config.set('watermark.image_path', 'C:\\logos\\company_logo.png')
    
    print("\nAfter changes:")
    print("Watermark config:", config.get_watermark_config())
