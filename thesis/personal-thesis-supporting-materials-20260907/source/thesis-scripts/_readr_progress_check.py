#!/usr/bin/env python3
import paramiko

HOST = "192.168.70.79"
PORT = 22
USER = "mx"
PASSWORD = "a123456"

cmd = (
    'cd /data1/rmx/projectb/AdsQA-main/evaluation/runs/readr_full7846_v1 && '
    'for f in 0 1 2 3 4; do '
    'n=$(find a0_mmr8/fold_$f -name prediction.json 2>/dev/null | wc -l); '
    'echo "fold_$f: $n"; done; '
    'echo "===ERRORS==="; '
    'grep -icE "error|traceback|failed" logs/a0_worker_gpu4_fold*.log logs/a0_worker_gpu5_fold*.log 2>/dev/null; '
    'echo "===GPU==="; '
    'nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader | sed -n "5,6p"; '
    'echo "===WORKERS==="; '
    'for p in pids/worker_gpu*.pid; do '
    'echo -n "$p: "; '
    'ps -o pid,etime,cmd -p $(cat $p 2>/dev/null) --no-headers 2>/dev/null || echo DEAD; done; '
    'echo "===DONE==="; '
    'ls A0_DONE 2>/dev/null || echo "not done"'
)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, PORT, USER, PASSWORD, timeout=30)

stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(out)
if err.strip():
    print("===STDERR===")
    print(err)
client.close()
