import shutil
import os

os.makedirs('/workspace/output/', exist_ok=True)
shutil.copy('diff_lr_ft_model.pth', '/workspace/output/diff_lr_ft_model.pth')
shutil.copy('metrics_diff_lr.json', '/workspace/output/metrics_diff_lr.json')
# best_score.json is already there based on my script