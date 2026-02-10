import subprocess
import time

print("Starting debug_pid check...")
try:
    start = time.time()
    # Using specific PID 45924 from logs/bot.pid
    old_pid = 45924
    print(f"Checking PID {old_pid} with tasklist...")
    
    # Replicating the exact command from run.py
    output = subprocess.check_output(
        ['tasklist', '/FI', f'PID eq {old_pid}', '/NH'],
        creationflags=0x08000000,
        stderr=subprocess.DEVNULL
    ).decode('utf-8', errors='ignore')
    
    print("Command finished!")
    print(f"Time taken: {time.time() - start:.4f}s")
    print(f"Output: {output.strip()}")
    
except Exception as e:
    print(f"Error: {e}")
