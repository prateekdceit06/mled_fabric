import socket
import sys

# Define the server IP address and port
server_ip = '10.0.0.100'
server_port = 50000
client_ip = '10.0.0.101'
client_port = 0


def get_master_config():
    try:
        # Create a socket object
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as e:
        print(f"Error creating socket: {e}")
        sys.exit(1)

    # Bind the socket to the client IP and port
    try:
        client_socket.bind((client_ip, client_port))
    except socket.error as e:
        print(f"Error on socket bind: {e}")
        sys.exit(1)

    try:
        # Connect to the server
        client_socket.connect((server_ip, server_port))
    except socket.gaierror as e:
        print(f"Address-related error connecting to server: {e}")
        sys.exit(1)
    except socket.error as e:
        print(f"Connection error: {e}")
        sys.exit(1)

    print(f"Connected to server at {server_ip}:{server_port}")

    transfer_complete = False

    # Receive file from the server
    with open('./1-1/master_config.json', 'wb') as f:
        while True:
            data = client_socket.recv(1024)  # Adjust the size based on the checksum length
            if not data:
                transfer_complete = True
                break
            f.write(data)

    if transfer_complete:
        print("Transfer completed.")
    # Close the connection
    try:
        client_socket.close()
    except socket.error as e:
        print(f"Error closing socket: {e}")
        sys.exit(1)


if __name__ == '__main__':
    get_master_config()
