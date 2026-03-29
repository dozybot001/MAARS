import os
import subprocess

try:
    result = subprocess.run(['find', '/', '-name', 'libgomp.so.1'], capture_output=True, text=True)
    print(result.stdout)
except Exception as e:
    print(e)