#!/usr/bin/env python3
"""Test the FileValidator functionality."""

from src.file_validator import FileValidator
from src.file_manager import FileManager
import os

# Change to project directory
os.chdir('c:/Users/CSE/Documents/miltiagent234')

# Initialize components
fm = FileManager('workspace')
validator = FileValidator(fm)

print("Testing FileValidator...")

# Test 1: Valid Python code
test_code = """def hello():
    print("Hello world")
    return True"""

is_valid, error = validator.validate_modification('test.py', test_code)
print(f"✅ Valid Python: {'PASS' if is_valid else 'FAIL'} - {error or 'No errors'}")

# Test 2: Invalid content (SQL in Python file)
invalid_code = """def hello()
    print("Hello world")
CREATE TABLE test"""

is_valid, error = validator.validate_modification('test.py', invalid_code)
print(f"✅ Invalid content detection: {'PASS' if not is_valid else 'FAIL'} - {error or 'No errors'}")

# Test 3: Valid requirements.txt
req_content = """flask==2.3.0
requests>=2.28.0
numpy"""

is_valid, error = validator.validate_modification('requirements.txt', req_content)
print(f"✅ Valid requirements.txt: {'PASS' if is_valid else 'FAIL'} - {error or 'No errors'}")

print("FileValidator tests completed!")