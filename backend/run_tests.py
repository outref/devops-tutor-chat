#!/usr/bin/env python3
"""
Simple test runner for the backend services.
Run with: python run_tests.py
"""

import subprocess
import sys
import os

def run_tests():
    """Run the test suite using pytest."""
    print("🚀 Running backend unit tests...")
    print("=" * 50)
    
    # Change to the backend directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # Run pytest with verbose output
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--tb=short",
            "--color=yes"
        ], capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
        else:
            print(f"\n❌ Some tests failed (exit code: {result.returncode})")
            
        return result.returncode
        
    except FileNotFoundError:
        print("❌ pytest not found. Please install it with: pip install pytest pytest-asyncio pytest-mock")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
