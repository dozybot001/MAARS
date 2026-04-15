import json
with open('/workspace/artifacts/r2_1/dynamic_sgd_log.json', 'r') as f:
    sgd_log = json.load(f)

print("SGD Epoch 10:", sgd_log[-1])