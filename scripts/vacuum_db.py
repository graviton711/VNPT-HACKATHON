import sqlite3
import os
import sys
import shutil
import time

DB_PATH = os.path.join("chroma_db", "chroma.sqlite3")
# Use User's Temp folder on C: to ensure write access and space
TEMP_DIR = os.getenv('TEMP') if os.getenv('TEMP') else "C:\\Temp"
TEMP_DB_PATH = os.path.join(TEMP_DIR, "chroma_vacuumed.sqlite3")

def vacuum_db_offload():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    # Check paths
    abs_db_path = os.path.abspath(DB_PATH)
    abs_temp_path = os.path.abspath(TEMP_DB_PATH)
    
    print(f"Source DB: {abs_db_path}")
    print(f"Temp DB Target (on C:): {abs_temp_path}")

    # clean up potential leftover
    if os.path.exists(abs_temp_path):
        try:
            os.remove(abs_temp_path)
        except Exception as e:
            print(f"Warning: Could not remove existing temp file: {e}")

    initial_size = os.path.getsize(abs_db_path) / (1024 * 1024 * 1024)
    print(f"Initial DB Size: {initial_size:.2f} GB")

    print("Connecting to database...")
    try:
        conn = sqlite3.connect(abs_db_path)
        
        # SQLite 'VACUUM INTO' creates a new vacuumed DB at the specified path
        # This allows us to use space on C: instead of E:
        sql = f"VACUUM INTO '{abs_temp_path}'" 
        print(f"Executing: {sql} ... (Please wait)")
        
        start_time = time.time()
        conn.execute(sql)
        conn.close()
        
        duration = time.time() - start_time
        print(f"VACUUM INTO completed in {duration:.1f} seconds.")

    except sqlite3.OperationalError as e:
        print(f"Error during VACUUM: {e}")
        print("Ensure disk space on C: is sufficient and DB is not locked.")
        return

    # Verification
    if not os.path.exists(abs_temp_path):
        print("Error: Temp file was not created. Aborting.")
        return
        
    new_size = os.path.getsize(abs_temp_path) / (1024 * 1024 * 1024)
    print(f"New DB Size: {new_size:.2f} GB")
    
    if new_size == 0:
        print("Error: New DB size is 0 bytes. Aborting.")
        return

    print(f"Reclaimed potential: {initial_size - new_size:.2f} GB")
    
    # Swapping files
    print("Swapping files (Replacing E: file with C: file)...")
    try:
        # 1. Backup/Remove old file
        # We delete directly because we don't have space for a backup on E: 
        # (That was the whole problem)
        print(f"Removing original file: {abs_db_path}")
        os.remove(abs_db_path)
        
        # 2. Move new file from C: to E:
        print(f"Moving {abs_temp_path} -> {abs_db_path}")
        shutil.move(abs_temp_path, abs_db_path)
        
        print("SUCCESS! Database vacuumed and restored.")
        
    except Exception as e:
        print(f"CRITICAL ERROR during file swap: {e}")
        print(f"Your new optimized database is currently at: {abs_temp_path}")
        print("Please manually move it to chroma_db/chroma.sqlite3")

if __name__ == "__main__":
    vacuum_db_offload()
