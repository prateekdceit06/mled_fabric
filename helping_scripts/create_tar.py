import subprocess

dir_path = "/home/prateek/Documents/FABRIC/mled_fabric/server"

# List of commands to run
commands = [
    "tar -czvf process_A.tar.gz process_A.py",
    "tar -czvf process_B.tar.gz process_B.py",
    "tar -czvf process_C.tar.gz process_C.py",
    "tar -czvf process_D.tar.gz process_D.py",
    "tar -czvf process_E.tar.gz process_E.py"
]

def run_commands_in_directory(commands, directory):
    for cmd in commands:
        # Change the working directory and run the command
        subprocess.run(cmd, cwd=directory, shell=True)

if __name__ == "__main__":
    run_commands_in_directory(commands, dir_path)

