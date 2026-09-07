from modelscope import snapshot_download

# 指定保存路径
local_dir = '/data1/rmx/projectb/models/MiniCPM-V-2_6'

model_dir = snapshot_download(
    'OpenBMB/MiniCPM-V-2_6', 
    cache_dir=local_dir, 
    revision='master'
)
print(f"模型已下载至: {model_dir}")