import os
import shutil

# 目标根目录
target_dir = "/data1/rmx/projectb/AdsQA-main/evaluation/results"

def process_copy_folders(directory):
    renamed_count = 0
    
    # 遍历目录
    # topdown=False 确保我们从最深层开始处理，虽然对于重命名文件夹这不是必须的，但通常更安全
    for root, dirs, files in os.walk(directory, topdown=False):
        
        # 遍历当前层级的所有文件夹
        for dirname in dirs:
            # 检查文件夹名是否以 " copy" 结尾
            if dirname.endswith(" copy"):
                source_path = os.path.join(root, dirname)
                
                # 构造新文件夹名：去掉结尾的 " copy"
                original_foldername = dirname[:-5] # 去掉最后5个字符 " copy"
                target_path = os.path.join(root, original_foldername)
                
                try:
                    # 1. 如果目标文件夹（原件）已经存在，必须先删除它
                    if os.path.exists(target_path):
                        # 再次确认是一个文件夹而不是同名文件
                        if os.path.isdir(target_path):
                            print(f"[删除旧原件] 正在删除: {target_path}")
                            shutil.rmtree(target_path)
                        else:
                            print(f"[跳过] 目标位置存在同名文件，非文件夹: {target_path}")
                            continue
                    
                    # 2. 将副本重命名为原件名
                    os.rename(source_path, target_path)
                    print(f"[成功] {dirname} -> {original_foldername}")
                    renamed_count += 1
                    
                except Exception as e:
                    print(f"[出错] 无法处理 {dirname}: {e}")

    print(f"\n处理完成。共重命名并覆盖了 {renamed_count} 个文件夹。")

if __name__ == "__main__":
    print(f"即将处理目录: {target_dir}")
    print("操作逻辑: 寻找 'xxx copy' 文件夹 -> 删除已存在的 'xxx' 文件夹 -> 将副本重命名为 'xxx'")
    confirm = input("❗ 高风险操作 (会删除旧原件)，确认请按 y，取消请按 n: ")
    
    if confirm.lower() == 'y':
        if os.path.exists(target_dir):
            process_copy_folders(target_dir)
        else:
            print(f"错误: 找不到目录 {target_dir}")
    else:
        print("操作已取消。")