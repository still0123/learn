import paramiko

HOST = "192.168.70.79"
PORT = 22
USER = "mx"
PASS = "a123456"

CMD = (
    "cd /data1/rmx/projectb/AdsQA-main/evaluation/runs/readr_full7846_v1 && "
    "echo '=== fold1 error lines (unique) ==='; "
    "grep -iE 'error|traceback|failed' logs/a0_worker_gpu5_fold1.log 2>/dev/null | sort | uniq -c | sort -rn | head -20; "
    "echo '=== fold0/2/3/4 error lines ==='; "
    "grep -ihE 'error|traceback|failed' logs/a0_worker_gpu4_fold0.log logs/a0_worker_gpu4_fold2.log logs/a0_worker_gpu4_fold4.log logs/a0_worker_gpu5_fold3.log 2>/dev/null | sort | uniq -c | sort -rn | head -20; "
    "echo '=== A0_DONE check ==='; ls -la A0_DONE 2>/dev/null || echo 'no A0_DONE marker'; "
    "echo '=== who is on GPU now ==='; "
    "nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader 2>/dev/null | head; "
    "echo '=== any a0 worker procs still alive ==='; "
    "ps aux | grep -iE 'a0_worker|readr' | grep -v grep | head"
)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, PORT, USER, PASS, timeout=30, banner_timeout=30, auth_timeout=30)
stdin, stdout, stderr = client.exec_command(CMD, timeout=180)
print(stdout.read().decode("utf-8", "replace"))
err = stderr.read().decode("utf-8", "replace")
if err.strip():
    print("===STDERR===")
    print(err)
client.close()
