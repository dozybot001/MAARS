#!/bin/bash
set -e
mkdir -p /workspace/results

echo "=== Running /001.py ==="
cd /workspace/results && python /workspace/artifacts/001.py

echo "=== Running /002.py ==="
cd /workspace/results && python /workspace/artifacts/002.py

echo "=== Running /003.py ==="
cd /workspace/results && python /workspace/artifacts/003.py

echo "=== Running 1/001.py ==="
cd /workspace/results && python /workspace/artifacts/1/001.py

echo "=== Running 2/001.py ==="
cd /workspace/results && python /workspace/artifacts/2/001.py

echo "=== Running 4/001.py ==="
cd /workspace/results && python /workspace/artifacts/4/001.py

echo "=== Running 3/001.py ==="
cd /workspace/results && python /workspace/artifacts/3/001.py

echo "=== Running 3/002.py ==="
cd /workspace/results && python /workspace/artifacts/3/002.py

echo "=== Running 3/003.py ==="
cd /workspace/results && python /workspace/artifacts/3/003.py

echo "=== Running 2/002.py ==="
cd /workspace/results && python /workspace/artifacts/2/002.py

echo "=== Running 2/003.py ==="
cd /workspace/results && python /workspace/artifacts/2/003.py

echo "=== Running 2/004.py ==="
cd /workspace/results && python /workspace/artifacts/2/004.py

echo "=== Running 2/005.py ==="
cd /workspace/results && python /workspace/artifacts/2/005.py

echo "=== Running 2/006.py ==="
cd /workspace/results && python /workspace/artifacts/2/006.py

echo "All experiments completed."