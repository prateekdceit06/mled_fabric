import os

# List of folder names
folders = ["1-1", "1-2", "1-3", "1-4", "1-5", "2-1", "2-3", "2-5", "3-1", "3-5"]

# Base directory where these folders are located
base_dir = "/home/prateek/Documents/FABRIC/mled_fabric"

def delete_file_from_folders(filename, folders, base_directory):
    for folder in folders:
        file_path = os.path.join(base_directory, folder, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Deleted {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

if __name__ == "__main__":
    delete_file_from_folders("process_config.json", folders, base_dir)

