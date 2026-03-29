import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    install('lightgbm')
    import lightgbm as lgb
    print("LightGBM version:", lgb.__version__)
except Exception as e:
    print("Failed to import LightGBM:", e)