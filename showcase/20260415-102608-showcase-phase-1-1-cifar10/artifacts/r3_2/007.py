try:
    with open('/workspace/artifacts/r3_1/008.py', 'r') as f:
        print(f.read())
except Exception as e:
    print(e)