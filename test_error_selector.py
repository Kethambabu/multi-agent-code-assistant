#!/usr/bin/env python3
"""Test the ErrorDrivenFileSelector functionality."""

from src.error_driven_selector import ErrorDrivenFileSelector
from src.file_manager import FileManager
import os

# Change to project directory
os.chdir('c:/Users/CSE/Documents/miltiagent234')

# Initialize components
fm = FileManager('workspace')
selector = ErrorDrivenFileSelector(fm)

print("Testing ErrorDrivenFileSelector...")

# Test 1: Error trace with file path
error_prompt = '''Fix this error:
Traceback (most recent call last):
  File "main.py", line 5, in __init__
    self.value = value
NameError: name 'value' is not defined'''

files = selector.select_files_from_error(error_prompt)
print(f"✅ Error trace selection: {files}")

# Test 2: No error trace
normal_prompt = 'Add a new function to calculate sum'
files2 = selector.select_files_from_error(normal_prompt)
print(f"✅ Normal prompt selection: {files2}")

# Test 3: Multiple files in trace
multi_error = '''Multiple errors:
  File "utils.py", line 10: syntax error
  File "main.py", line 20: import error'''

files3 = selector.select_files_from_error(multi_error)
print(f"✅ Multiple files selection: {files3}")

print("ErrorDrivenFileSelector tests completed!")