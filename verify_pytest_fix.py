#!/usr/bin/env python3
"""
Verification script for pytest test discovery fix.
This script tests the key components of the pytest configuration.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def verify_vscode_settings():
    """Verify that VSCode settings are correctly configured"""
    settings_path = Path(".vscode/settings.json")
    if not settings_path.exists():
        print("❌ VSCode settings file not found")
        return False

    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        required_keys = [
            "python.testing.pytestEnabled",
            "python.testing.pytestArgs",
            "python.testing.cwd"
        ]

        for key in required_keys:
            if key not in settings:
                print(f"❌ Missing required setting: {key}")
                return False

        # Check for explicit rootdir path
        pytest_args = settings["python.testing.pytestArgs"]
        rootdir_found = any("--rootdir=d:\\projects\\Omega_KG_dev" in arg for arg in pytest_args)
        if not rootdir_found:
            print("❌ --rootdir argument not found or incorrect in pytestArgs")
            return False

        # Check for explicit working directory
        if settings["python.testing.cwd"] != "d:\\projects\\Omega_KG_dev":
            print("❌ Incorrect working directory in python.testing.cwd")
            return False

        print("✅ VSCode settings verified successfully")
        return True

    except Exception as e:
        print(f"❌ Error reading VSCode settings: {e}")
        return False

def verify_pytest_ini():
    """Verify that pytest.ini is correctly configured"""
    pytest_ini_path = Path("tests/pytest.ini")
    if not pytest_ini_path.exists():
        print("❌ pytest.ini file not found")
        return False

    try:
        with open(pytest_ini_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for required configurations
        checks = [
            ("pythonpath = .", "pythonpath setting"),
            ("WORKSPACE_ROOT=d:\\\\projects\\\\Omega_KG_dev", "explicit workspace root"),
            ("testpaths = tests", "testpaths setting")
        ]

        for check, description in checks:
            if check not in content:
                print(f"❌ Missing {description} in pytest.ini")
                return False

        print("✅ pytest.ini verified successfully")
        return True

    except Exception as e:
        print(f"❌ Error reading pytest.ini: {e}")
        return False

def test_manual_pytest_execution():
    """Test manual pytest execution"""
    try:
        # Test collecting tests from a specific file
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "tests/test_verify_system.py", "--collect-only"
        ], capture_output=True, text=True, cwd="d:\\projects\\Omega_KG_dev")

        if result.returncode != 0:
            print(f"❌ Manual pytest execution failed: {result.stderr}")
            return False

        if "collected 0 items" in result.stdout:
            print("❌ No tests collected from test file")
            return False

        print("✅ Manual pytest execution verified successfully")
        return True

    except Exception as e:
        print(f"❌ Error during manual pytest execution: {e}")
        return False

def test_python_path():
    """Test that Python path includes project root"""
    try:
        result = subprocess.run([
            sys.executable, "-c",
            "import sys; print('\\n'.join(sys.path))"
        ], capture_output=True, text=True, cwd="d:\\projects\\Omega_KG_dev")

        if result.returncode != 0:
            print(f"❌ Python path test failed: {result.stderr}")
            return False

        # Check if project root is in Python path
        if "d:\\projects\\Omega_KG_dev" not in result.stdout:
            print("❌ Project root not found in Python path")
            return False

        print("✅ Python path verification successful")
        return True

    except Exception as e:
        print(f"❌ Error testing Python path: {e}")
        return False

def main():
    """Run all verification tests"""
    print("🔍 Verifying pytest test discovery fix...")
    print("=" * 50)

    tests = [
        ("VSCode settings verification", verify_vscode_settings),
        ("pytest.ini configuration", verify_pytest_ini),
        ("Manual pytest execution", test_manual_pytest_execution),
        ("Python path verification", test_python_path)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        result = test_func()
        results.append((test_name, result))

    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n📈 Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All verification tests passed! The pytest test discovery fix is working correctly.")
        print("\nNext steps:")
        print("1. Restart VSCode")
        print("2. Open Test Explorer")
        print("3. Click 'Refresh Tests'")
        print("4. Verify tests appear in the Test Explorer")
    else:
        print("\n⚠️  Some verification tests failed. Please check the configuration:")
        print("- Ensure VSCode is restarted after making changes")
        print("- Verify the paths in .vscode/settings.json")
        print("- Check pytest.ini configuration")
        print("- Ensure the virtual environment is activated")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)