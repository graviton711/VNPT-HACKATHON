import shutil
import os
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/switch_config.py [public|private]")
        return

    mode = sys.argv[1].lower()
    src_dir = os.path.join(os.path.dirname(__file__), '../src')
    config_path = os.path.join(src_dir, 'config.py')
    
    if mode == 'private':
        source = os.path.join(src_dir, 'config_private.py')
        print("Switching to PRIVATE test configuration (Turbo Mode)...")
    elif mode == 'public':
        source = os.path.join(src_dir, 'config_public.py')
        print("Switching to PUBLIC test configuration (Safe Mode)...")
    else:
        print("Invalid mode. Use 'public' or 'private'.")
        return

    if os.path.exists(source):
        shutil.copyfile(source, config_path)
        print(f"Success! {config_path} has been updated to {mode} mode.")
    else:
        print(f"Error: Source config {source} not found. Please ensure it exists.")

if __name__ == "__main__":
    main()
