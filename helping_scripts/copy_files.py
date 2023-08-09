import os
import shutil

# Base directory where these folders are located
base_dir = "/home/prateek/Documents/FABRIC/mled_fabric"

# List of folders and files
folders = ["1-1", "1-2", "1-3", "1-4", "1-5", "2-1", "2-3", "2-5", "3-1", "3-5"]
files_to_copy = ["config.py", "master_config.py", "process_config.py", "start.py", "utils.py"]


def copy_files(source_folder, dest_folder, files):
    for file in files:
        source_file_path = os.path.join(base_dir, source_folder, file)
        dest_file_path = os.path.join(base_dir, dest_folder, file)

        # Check if the file exists in the source folder
        if os.path.exists(source_file_path):
            # Copy the file to the destination folder, overwriting if it exists
            shutil.copy2(source_file_path, dest_file_path)
            print(f"File {file} copied successfully to {dest_folder}")


if __name__ == "__main__":
    for folder in folders[1:]:  # Start from the second folder since we're copying from the first one
        copy_files("1-1", folder, files_to_copy)
