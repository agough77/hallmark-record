"""
Integration Test for Hallmark Record Wizard Editor
Tests the complete workflow
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from editor.wizard_editor import WizardEditor
from config_manager import ConfigManager

def test_config_manager():
    """Test configuration manager"""
    print("Testing Configuration Manager...")
    
    config = ConfigManager()
    
    # Test getting values
    output_folder = config.get_output_folder()
    print(f"  ✓ Output folder: {output_folder}")
    
    watermark = config.get_watermark_config()
    print(f"  ✓ Watermark config: {watermark}")
    
    export_settings = config.get_export_settings()
    print(f"  ✓ Export settings: {export_settings}")
    
    # Test setting values
    config.set('watermark.enabled', True)
    config.set('export.default_quality', 'high')
    print("  ✓ Set configuration values")
    
    # Verify changes
    assert config.get('watermark.enabled') == True
    assert config.get('export.default_quality') == 'high'
    print("  ✓ Configuration changes verified")
    
    print("✓ Configuration Manager tests passed!\n")
    return True


def test_wizard_editor_creation():
    """Test wizard editor creation"""
    print("Testing Wizard Editor Creation...")
    
    app = QApplication(sys.argv)
    
    # Test with no session
    editor = WizardEditor()
    print("  ✓ Created editor without session")
    
    # Test with session folder
    session = r"C:\Users\AGough\Downloads\Hallmark Record\session_20260108_093907"
    if os.path.exists(session):
        editor_with_session = WizardEditor(session)
        print(f"  ✓ Created editor with session: {session}")
    else:
        print(f"  ⚠ Session folder not found (testing only): {session}")
    
    print("✓ Wizard Editor creation tests passed!\n")
    return True


def test_ffmpeg_detection():
    """Test FFmpeg detection"""
    print("Testing FFmpeg Detection...")
    
    from editor.wizard_editor import WizardEditor
    
    app = QApplication(sys.argv)
    editor = WizardEditor()
    
    # Check if FFmpeg path is set
    ffmpeg_path = editor.ffmpeg_path
    print(f"  FFmpeg path: {ffmpeg_path}")
    
    if ffmpeg_path and ffmpeg_path != "ffmpeg":
        if os.path.exists(ffmpeg_path):
            print(f"  ✓ FFmpeg found at: {ffmpeg_path}")
        else:
            print(f"  ⚠ FFmpeg path set but file not found: {ffmpeg_path}")
    else:
        print("  ⚠ FFmpeg using system PATH")
    
    print("✓ FFmpeg detection test complete!\n")
    return True


def test_wizard_pages():
    """Test wizard page navigation"""
    print("Testing Wizard Pages...")
    
    app = QApplication(sys.argv)
    editor = WizardEditor()
    
    # Test page count
    page_count = editor.stacked_widget.count()
    assert page_count == 5, f"Expected 5 pages, found {page_count}"
    print(f"  ✓ All 5 wizard pages created")
    
    # Test navigation
    editor.next_step()
    assert editor.stacked_widget.currentIndex() == 1
    print("  ✓ Next step navigation works")
    
    editor.previous_step()
    assert editor.stacked_widget.currentIndex() == 0
    print("  ✓ Previous step navigation works")
    
    # Test page widgets
    assert editor.page1 is not None
    assert editor.page2 is not None
    assert editor.page3 is not None
    assert editor.page4 is not None
    assert editor.page5 is not None
    print("  ✓ All page widgets initialized")
    
    print("✓ Wizard page tests passed!\n")
    return True


def run_all_tests():
    """Run all integration tests"""
    print("=" * 60)
    print("HALLMARK RECORD - Integration Tests")
    print("=" * 60)
    print()
    
    tests = [
        ("Configuration Manager", test_config_manager),
        ("Wizard Editor Creation", test_wizard_editor_creation),
        ("FFmpeg Detection", test_ffmpeg_detection),
        ("Wizard Pages", test_wizard_pages),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"✗ {name} failed\n")
        except Exception as e:
            failed += 1
            print(f"✗ {name} failed with exception: {e}\n")
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
