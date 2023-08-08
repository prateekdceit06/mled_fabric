import os

def run_command(base_ip, base_label, repetitions):
    ip_parts = base_ip.split('.')
    last_octet = int(ip_parts[-1])

    for i in range(repetitions):
        ip = '.'.join(ip_parts[:-1]) + '.' + str(last_octet + i)
        label = base_label + str(i + 1)
        command = f"sudo ip addr add {ip}/24 dev enp0s3 label {label}"
        os.system(command)
        print(f"Created interface {label} with ip {ip}/24 successfully")

if __name__ == "__main__":
    run_command("10.0.0.100", "enp0s3:", 10)

