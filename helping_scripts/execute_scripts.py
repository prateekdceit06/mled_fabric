import subprocess
import time


def execute_python_script(script_name):
    try:
        subprocess.run(["python3", script_name], check=True)
        print(f"Executed {script_name} successfully.")
    except subprocess.CalledProcessError:
        print(f"Error executing {script_name}.")


if __name__ == "__main__":
    scripts = ["clean_up.py", "copy_files.py", "change_ip.py"]

    for script in scripts:
        execute_python_script(script)
        time.sleep(5)
