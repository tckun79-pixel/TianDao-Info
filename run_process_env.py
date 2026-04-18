#!/usr/bin/env python3
import subprocess, os

# Read and source bashrc manually to get env vars
env = os.environ.copy()
bashrc_path = os.path.expanduser('~/.bashrc')
with open(bashrc_path) as f:
    content = f.read()

# Parse exports from bashrc
for line in content.split('\n'):
    if line.strip().startswith('export '):
        parts = line[7:].split('=', 1)
        if len(parts) == 2:
            key = parts[0].strip()
            val = parts[1].strip().strip('\"').strip('\n')
            if 'SUPABASE' in key:
                env[key] = val
                print(f'Set {key}')

# Run process_quotes.py with updated env
result = subprocess.run(['python3', '/home/ck_kun/TianDao-Info/process_quotes.py'],
    env=env, capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr)