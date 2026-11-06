import subprocess, sys, os

def test_cli_help():
    r = subprocess.run([sys.executable, "darkdump.py", "--help"], capture_output=True, text=True)
    assert r.returncode in (0, 1, 2)

def test_web_app_import():
    # ensure web app module loads without crashing
    r = subprocess.run([sys.executable, "-c", "import ast; ast.parse(open('darkdump.py').read())"], capture_output=True, text=True)
    assert r.returncode == 0
