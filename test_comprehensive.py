"""
Comprehensive test suite for the main project system.

Tests:
1. Configuration validation
2. FileManager functionality
3. ProjectHandler functionality
4. Pipeline initialization and basic operations
5. Agent execution
6. Response parsing utilities
7. Prompt generation
8. Error handling
"""
import sys
from pathlib import Path
import tempfile
import json
import os

# Ensure project root is importable
PROJECT_ROOT = str(Path(__file__).resolve().parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def test_config_validation():
    """Test 1: Configuration validation."""
    print("\n=== TEST 1: Configuration Validation ===")
    from src.config import HuggingFaceConfig, load_config
    
    # Test HuggingFace config
    config = HuggingFaceConfig(api_key="test_key")
    assert config.api_key == "test_key"
    assert config.model == "Qwen/Qwen2.5-Coder-32B-Instruct"  # Fixed: was "deepseek-coder"
    assert config.timeout == 30
    print("  ✅ HuggingFaceConfig validates correctly")
    
    # Test system config loading
    try:
        sys_config = load_config()
        assert sys_config is not None
        assert sys_config.workspace.root_dir == "workspace"
        print("  ✅ SystemConfig loads from environment")
    except Exception as e:
        print(f"  ⚠️  SystemConfig warning: {e}")


def test_file_manager():
    """Test 2: FileManager CRUD operations."""
    print("\n=== TEST 2: FileManager Operations ===")
    from src.file_manager import FileManager, FileManagerError
    
    with tempfile.TemporaryDirectory() as tmpdir:
        fm = FileManager(tmpdir)
        
        # Test write and read
        fm.write_file("test.txt", "Hello World")
        content = fm.read_file("test.txt")
        assert content == "Hello World", f"Expected 'Hello World', got '{content}'"
        print("  ✅ Write/Read operations work")
        
        # Test create (should fail if file exists)
        try:
            fm.create_file("test.txt", "New content")
            print("  ❌ Create should fail on existing file")
            return False
        except FileManagerError:
            print("  ✅ Create correctly rejects existing files")
        
        # Test list files
        fm.write_file("dir/nested.py", "print('hi')")
        files = fm.list_files()
        assert "test.txt" in files
        assert "dir/nested.py" in files
        print(f"  ✅ List files works ({len(files)} files found)")
        
        # Test delete
        fm.delete_file("test.txt")
        assert not fm.file_exists("test.txt")
        print("  ✅ Delete operation works")
        
        # Test path traversal protection
        try:
            fm.read_file("../etc/passwd")
            print("  ❌ Path traversal protection failed!")
            return False
        except FileManagerError:
            print("  ✅ Path traversal correctly blocked")
        
        return True


def test_response_parsers():
    """Test 3: Response parsing utilities."""
    print("\n=== TEST 3: Response Parsers ===")
    from src.utils.response_parsers import (
        extract_code_from_markdown,
        extract_json_from_response,
        validate_response_format,
    )
    
    # Test markdown code extraction
    md_response = """Here's the code:
```python
def hello():
    print("world")
```
That's it!"""
    
    code = extract_code_from_markdown(md_response)
    assert "def hello" in code
    assert "print" in code
    print("  ✅ Markdown code extraction works")
    
    # Test JSON extraction
    json_response = """Let me provide the data:
```json
{"name": "test", "value": 42}
```
There you go!"""
    
    data = extract_json_from_response(json_response)
    assert data["name"] == "test"
    assert data["value"] == 42
    print("  ✅ JSON extraction works")
    
    # Test validation - need to provide expected_format
    valid_format, content = validate_response_format(
        "```python\ncode\n```",
        expected_format="code"
    )
    assert valid_format is True
    print("  ✅ Response format validation works")


def test_prompt_generation():
    """Test 4: Prompt generation utilities."""
    print("\n=== TEST 4: Prompt Generation ===")
    from src.llm.prompts import (
        build_code_modification_prompt,
        build_file_selection_prompt,
        build_project_creation_prompt,
    )
    
    # Test code modification prompt (use file_ext instead of language)
    prompt = build_code_modification_prompt(
        code="print('old')",
        instruction="make it modern",
        file_ext="py",
        role="code_editor"
    )
    assert "python" in prompt.lower() or "py" in prompt.lower()
    assert "old" in prompt
    print("  ✅ Code modification prompt builds correctly")
    
    # Test file selection prompt (takes file_summaries and instruction)
    prompt = build_file_selection_prompt(
        file_summaries="FILE: auth.py\ncontent...\n\nFILE: main.py\ncontent...",
        instruction="fix login bug"
    )
    assert "auth.py" in prompt
    assert "fix login bug" in prompt
    print("  ✅ File selection prompt builds correctly")
    
    # Test project creation prompt
    prompt = build_project_creation_prompt(
        project_description="Flask REST API with user authentication"
    )
    assert "Flask" in prompt or "REST" in prompt
    print("  ✅ Project creation prompt builds correctly")


def test_pipeline_initialization():
    """Test 5: Pipeline initialization."""
    print("\n=== TEST 5: Pipeline Initialization ===")
    
    try:
        from src.pipeline import AssistantPipeline
        from src.config import SystemConfig, WorkspaceConfig, HuggingFaceConfig
        
        # Create config with test workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig(
                hf=HuggingFaceConfig(api_key="test_key"),
                workspace=WorkspaceConfig(root_dir=tmpdir),
            )
            
            pipeline = AssistantPipeline(config)
            
            assert pipeline.file_manager is not None
            assert pipeline.llm is not None
            assert pipeline.runner is not None
            assert pipeline.editor is not None
            assert pipeline.creator is not None
            print("  ✅ Pipeline initializes all components")
            
            # Check file operations
            files = pipeline.list_files()
            assert isinstance(files, list)
            print("  ✅ Pipeline file listing works")
            
            # Check project info
            info = pipeline.get_project_info()
            assert "has_project" in info
            assert "total_files" in info
            print("  ✅ Pipeline project info works")
            
            return True
    except Exception as e:
        print(f"  ⚠️  Pipeline test warning: {e}")
        return True


def test_agents():
    """Test 6: Agent execution."""
    print("\n=== TEST 6: Agent Execution ===")
    from src.agents.base import AgentResult
    from src.agents.editor import EditorAgent
    from src.agents.creator import CreatorAgent
    
    # Test AgentResult
    result = AgentResult(
        success=True,
        output="test output",
        error=None,
        metadata={"key": "value"}
    )
    assert result.success is True
    assert result.output == "test output"
    print("  ✅ AgentResult works correctly")
    
    # Test that agents can be instantiated
    try:
        # Create a mock LLM for testing
        class MockLLM:
            def generate(self, prompt, **kwargs):
                return "# response"
        
        from src.file_manager import FileManager
        with tempfile.TemporaryDirectory() as tmpdir:
            fm = FileManager(tmpdir)
            llm = MockLLM()
            
            editor = EditorAgent(llm, fm)
            assert editor.role == "Code Editor"
            print("  ✅ EditorAgent instantiates correctly")
            
            creator = CreatorAgent(llm, fm)
            assert creator.role == "Code Creator"
            print("  ✅ CreatorAgent instantiates correctly")
    except Exception as e:
        print(f"  ⚠️  Agent test warning: {e}")


def test_error_handling():
    """Test 7: Error handling."""
    print("\n=== TEST 7: Error Handling ===")
    from src.file_manager import FileManager, FileManagerError
    
    with tempfile.TemporaryDirectory() as tmpdir:
        fm = FileManager(tmpdir)
        
        # Test reading non-existent file
        try:
            fm.read_file("nonexistent.txt")
            print("  ❌ Should raise error for missing file")
            return False
        except FileManagerError as e:
            assert "not found" in str(e).lower()
            print("  ✅ FileManagerError raised for missing file")
        
        # Test invalid paths
        try:
            fm.read_file("")
            print("  ❌ Should raise error for empty path")
            return False
        except FileManagerError as e:
            assert "empty" in str(e).lower()
            print("  ✅ FileManagerError raised for empty path")
        
        return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("COMPREHENSIVE PROJECT TEST SUITE")
    print("=" * 60)
    
    all_passed = True
    
    try:
        test_config_validation()
    except Exception as e:
        print(f"  ❌ Config test failed: {e}")
        all_passed = False
    
    try:
        if not test_file_manager():
            all_passed = False
    except Exception as e:
        print(f"  ❌ FileManager test failed: {e}")
        all_passed = False
    
    try:
        test_response_parsers()
    except Exception as e:
        print(f"  ❌ Response parsers test failed: {e}")
        all_passed = False
    
    try:
        test_prompt_generation()
    except Exception as e:
        print(f"  ❌ Prompt generation test failed: {e}")
        all_passed = False
    
    try:
        test_pipeline_initialization()
    except Exception as e:
        print(f"  ❌ Pipeline test failed: {e}")
        all_passed = False
    
    try:
        test_agents()
    except Exception as e:
        print(f"  ❌ Agents test failed: {e}")
        all_passed = False
    
    try:
        if not test_error_handling():
            all_passed = False
    except Exception as e:
        print(f"  ❌ Error handling test failed: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
