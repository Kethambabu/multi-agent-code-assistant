#!/usr/bin/env python3
"""
Validation tests for implementation phases.

Run: python test_phases.py
"""
import tempfile
import traceback
import json
import sys


def test_phase_1():
    """Test Phase 1: FileManager"""
    from src.file_manager import FileManager
    
    print("\n=== PHASE 1: FileManager ===")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            fm = FileManager(tmpdir)
            
            # Test create
            fm.create_file('test.py', 'print(1)')
            content = fm.read_file('test.py')
            assert content == 'print(1)', f'Create/read failed: {content}'
            
            # Test list
            files = fm.list_files()
            assert 'test.py' in files, f'List failed: {files}'
            
            # Test exists
            assert fm.file_exists('test.py'), 'Exists check failed'
            
            # Test write
            fm.write_file('test.py', 'print(2)')
            assert fm.read_file('test.py') == 'print(2)', 'Write failed'
            
            # Test delete
            fm.delete_file('test.py')
            assert not fm.file_exists('test.py'), 'Delete failed'
            
        print("✓ PASS: FileManager - All tests passed")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        traceback.print_exc()
        return False


def test_phase_2():
    """Test Phase 2: ProjectHandler"""
    from src.file_manager import FileManager
    from src.project_handler import ProjectHandler
    
    print("\n=== PHASE 2: ProjectHandler ===")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            fm = FileManager(tmpdir)
            ph = ProjectHandler(fm)
            
            # Test empty workspace
            info = ph.get_project_info()
            assert info['has_project'] == False, f'Should be empty: {info}'
            assert info['total_files'] == 0, f'Should have 0 files: {info}'
            
            # Create file
            fm.create_file('main.py', 'print("hello")')
            info = ph.get_project_info()
            assert info['has_project'] == True, f'Should have project: {info}'
            assert info['total_files'] == 1, f'Should have 1 file: {info}'
            
            # Test clear
            ph.clear_workspace()
            info = ph.get_project_info()
            assert info['total_files'] == 0, f'Should be empty after clear: {info}'
            
        print("✓ PASS: ProjectHandler - All tests passed")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        traceback.print_exc()
        return False


def test_phase_6():
    """Test Phase 6: ProjectRunner"""
    from src.file_manager import FileManager
    from src.runner import ProjectRunner
    
    print("\n=== PHASE 6: ProjectRunner ===")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            fm = FileManager(tmpdir)
            runner = ProjectRunner(fm, timeout=5)
            
            # Create a simple test file
            fm.create_file('hello.py', 'print("Hello from runner")')
            
            # Run it
            result = runner.run('hello.py')
            assert result.success, f'Run should succeed: {result.stderr}'
            assert 'Hello from runner' in result.stdout, f'Output mismatch: {result.stdout}'
            
        print("✓ PASS: ProjectRunner - All tests passed")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        traceback.print_exc()
        return False


def test_phases_integration():
    """Test basic pipeline integration"""
    from src.config import load_config
    from src.pipeline import AssistantPipeline
    
    print("\n=== INTEGRATION: Pipeline ===")
    try:
        config = load_config()
        pipeline = AssistantPipeline(config)
        
        # Check initialization
        assert pipeline.file_manager is not None, 'FileManager  failed'
        assert pipeline.project_handler is not None, 'ProjectHandler not initialized'
        assert pipeline.runner is not None, 'Runner not initialized'
        assert len(pipeline.registry.list_agents()) > 0, 'No agents registered'
        
        print("✓ PASS: Pipeline - Integration initialization successful")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("IMPLEMENTATION PHASE VALIDATION TESTS")
    print("="*60)
    
    results = {
        "Phase 1 (FileManager)": test_phase_1(),
        "Phase 2 (ProjectHandler)": test_phase_2(),
        "Phase 6 (ProjectRunner)": test_phase_6(),
        "Integration (Pipeline)": test_phases_integration(),
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for phase, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {phase}")
    
    all_passed = all(results.values())
    print("\n" + ("="*60))
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("="*60)
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
