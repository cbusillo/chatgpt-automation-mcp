#!/usr/bin/env python3
import subprocess
import os

# Test different ways of launching Chrome
chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
user_data_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome-Automation")

print(f"Chrome path: {chrome_path}")
print(f"User data dir: {user_data_dir}")
print(f"User data dir exists: {os.path.exists(user_data_dir)}")

# Method 1: List with separate arguments (current approach)
cmd1 = [chrome_path, "--remote-debugging-port=9222", "--user-data-dir", user_data_dir, "https://chatgpt.com"]
print(f"\nMethod 1 (list with separate args): {cmd1}")

# Method 2: List with equals sign
cmd2 = [chrome_path, "--remote-debugging-port=9222", f"--user-data-dir={user_data_dir}", "https://chatgpt.com"]
print(f"\nMethod 2 (list with equals): {cmd2}")

# Method 3: Check if profile directory needs to exist first
default_dir = os.path.join(user_data_dir, "Default")
print(f"\nDefault directory exists: {os.path.exists(default_dir)}")

# Let's create the directory structure if it doesn't exist
if not os.path.exists(user_data_dir):
    print(f"Creating directory: {user_data_dir}")
    os.makedirs(user_data_dir, exist_ok=True)
    
if not os.path.exists(default_dir):
    print(f"Creating Default profile directory: {default_dir}")
    os.makedirs(default_dir, exist_ok=True)

# Create First Run file to prevent setup
first_run = os.path.join(user_data_dir, "First Run")
if not os.path.exists(first_run):
    print(f"Creating First Run file: {first_run}")
    open(first_run, 'a').close()

print("\nNow try launching with subprocess...")
print("Command:", ' '.join(cmd1))

# Actually run it
# process = subprocess.Popen(cmd1)
# print(f"Launched with PID: {process.pid}")