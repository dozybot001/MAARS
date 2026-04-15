import json

with open('/workspace/artifacts/r2_1/dynamic_sgd_log.json', 'r') as f:
    sgd_log = json.load(f)

print("SGD Log Keys:", sgd_log[0].keys() if isinstance(sgd_log, list) else sgd_log.keys())
if isinstance(sgd_log, list):
    print("SGD Log Sample (Epoch 0):", sgd_log[0])
    print("Number of epochs:", len(sgd_log))
else:
    # Maybe it's a dict of lists
    for k in sgd_log:
        print(f"{k}: {len(sgd_log[k])} items")