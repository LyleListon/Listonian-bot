import sys
import os
import platform

print("Python version:", sys.version)
print("Python executable:", sys.executable)
print("Platform:", platform.platform())
print("Current directory:", os.getcwd())
print("Does venv Python exist?", os.path.exists(os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")))