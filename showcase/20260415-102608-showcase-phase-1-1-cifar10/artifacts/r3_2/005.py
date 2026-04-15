import torch

def check_model(path):
    print(f"\nChecking {path}:")
    try:
        sd = torch.load(path, map_location='cpu')
        keys = list(sd.keys())
        print(f"Total keys: {len(keys)}")
        for k in keys[-5:]:
            print(f"{k}: {sd[k].shape}")
    except Exception as e:
        print(f"Error: {e}")

check_model('/workspace/artifacts/1/source_badnets.pth')
check_model('/workspace/artifacts/r3_1/diff_lr_ft_model.pth')