import subprocess
import os

# Base directory where these folders are located
base_dir = "/home/prateek/Documents/FABRIC/mled_fabric"

# List of folders
folders = ["1-1", "1-2", "1-3", "1-4", "1-5", "2-1", "2-3", "2-5", "3-1", "3-5"]

def run_start_in_folder(folder):
    file_path = os.path.join(base_dir, folder, "start.py")
    
    # Check if the file exists in the folder
    if os.path.exists(file_path):
        try:
            # Run the file using python3
            subprocess.run(["python3", file_path], check=True)
            print(f"Executed start.py in {folder} successfully.")
        except subprocess.CalledProcessError:
            print(f"Error executing start.py in {folder}")

if __name__ == "__main__":
    for folder in folders:
        run_start_in_folder(folder)

