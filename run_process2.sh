#!/usr/bin/env python3
import subprocess, os

# Source bashrc and run process_quotes.py
result = subprocess.run(['bash', '-i', '-c', 
    'source ~/.bashrc && cd /home/ck_kun/TianDao-Info && python3 process_quotes.py'],
    capture_output=True, text=True)
print(result.stdout)
print(result.stderr)