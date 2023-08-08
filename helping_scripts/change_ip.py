import os

# Base directory where these folders are located
base_dir = "/home/prateek/Documents/FABRIC/mled_fabric"

# Mapping of folder names to client_ip values
folder_to_ip = {
    "1-1": "10.0.0.101",
    "1-2": "10.0.0.102",
    "1-3": "10.0.0.103",
    "1-4": "10.0.0.104",
    "1-5": "10.0.0.105",
    "2-1": "10.0.0.106",
    "2-3": "10.0.0.107",
    "2-5": "10.0.0.108",
    "3-1": "10.0.0.100",
    "3-5": "10.0.0.109"
}

def update_client_ip(folder, ip):
    file_path = os.path.join(base_dir, folder, "start.py")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace the client_ip value
        new_content = content.replace("client_ip = '10.0.0.101'", f"client_ip = '{ip}'")
        
        with open(file_path, 'w') as f:
            f.write(new_content)
            file_name = os.path.basename(file_path)
            print(f"IP in {file_name} changed to {ip}")

if __name__ == "__main__":
    for folder, ip in folder_to_ip.items():
        update_client_ip(folder, ip)

