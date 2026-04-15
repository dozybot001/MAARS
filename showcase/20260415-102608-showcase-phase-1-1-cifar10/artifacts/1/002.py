import sys
import os

print(sys.executable)
print(sys.path)

try:
    import torch
    print(f"Torch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
except ImportError as e:
    print(f"ImportError: {e}")

try:
    import torchvision
    print(f"Torchvision version: {torchvision.__version__}")
except ImportError as e:
    print(f"ImportError: {e}")