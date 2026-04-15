# Attempting to install torch and torchvision
import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    install("torch")
    install("torchvision")
    install("numpy")
    install("pillow")
    print("Installation successful")
except Exception as e:
    print(f"Installation failed: {e}")