from crc import CRC
from checksum import Checksum
from header import fixed_format, Header
from packet import Packet

import struct


class SendReceive:

    def get_value_to_check(self, chunk, method, parameter):
        if method == "crc":
            crc_obj = CRC(parameter)
            value = crc_obj.calculate(chunk)
        elif method == "checksum":
            checksum_obj = Checksum(parameter)
            value = checksum_obj.calculate(chunk)
        return value

    def verify_value(self, chunk, value_to_compare, method, parameter):
        if method == "crc":
            crc_obj = CRC(parameter)
            value = crc_obj.verify(chunk, value_to_compare)
        elif method == "checksum":
            checksum_obj = Checksum(parameter)
            value = checksum_obj.verify(chunk, value_to_compare)
        return value

    def send_data(self, sending_socket, packet):
        header = packet.header
        packed_header = header.pack()
        chunk = packet.chunk
        sending_socket.sendall(packed_header)
        sending_socket.send(header.check_value.encode())
        sending_socket.sendall(struct.pack(
            f"{header.size_of_errors}i", *header.errors))

        sending_socket.sendall(chunk)

    def receive_data(self, receiving_sock):
        fixed_data = receiving_sock.recv(struct.calcsize(fixed_format))
        received_seq_num, received_src, received_dest, received_size_of_check_value, received_size_of_chunk, received_ack_byte, received_size_of_errors, received_last_packet = struct.unpack(
            fixed_format, fixed_data)

        received_check_value_data = receiving_sock.recv(
            received_size_of_check_value)

        received_errors_format = f"{received_size_of_errors}i"
        received_errors_data = receiving_sock.recv(
            struct.calcsize(received_errors_format))
        # received_errors = list(struct.unpack(
        #     received_errors_format, received_errors_data))
        received_chunk_data = receiving_sock.recv(received_size_of_chunk)

        return received_seq_num, received_src, received_dest, received_check_value_data, received_chunk_data, received_ack_byte, fixed_data, received_errors_data, received_last_packet

    def decapsulate(self, data):
        fixed_size = struct.calcsize(fixed_format)
        fixed_data = data[:fixed_size]
        received_seq_num, received_src, received_dest, received_size_of_check_value, received_size_of_chunk, received_ack_byte, received_size_of_errors, received_last_packet = struct.unpack(
            fixed_format, fixed_data)

        offset = fixed_size
        received_check_value_data = data[offset:offset +
                                         received_size_of_check_value]
        offset += received_size_of_check_value

        received_errors_format = f"{received_size_of_errors}i"
        received_errors_size = struct.calcsize(received_errors_format)
        received_errors_data = data[offset:offset+received_errors_size]
        offset += received_errors_size

        received_chunk_data = data[offset:offset+received_size_of_chunk]

        header = Header(received_seq_num, received_src.decode(), received_dest.decode(), received_check_value_data.decode(
        ), received_size_of_chunk, received_ack_byte, received_errors_data, received_last_packet)
        packet = Packet(header, received_chunk_data)

        return packet

    def send_ack(self, sending_socket, packet):
        header = packet.header
        packed_header = header.pack()
        chunk = packet.chunk
        sending_socket.sendall(packed_header)
        sending_socket.send(header.check_value.encode())
        sending_socket.sendall(struct.pack(
            f"{header.size_of_errors}i", *header.errors))

        sending_socket.sendall(chunk)

    def add_error(self, data, error_introduction_location, method, parameter):

        new_data = data

        if method == "checksum":
            parameter = int(parameter)

            if len(data) >= error_introduction_location+1+(2*parameter):

                # Check if the checksum length is valid
                if parameter <= 0 or parameter > len(data):
                    raise ValueError("Invalid checksum length")

                error_introduction_location = error_introduction_location - \
                    (error_introduction_location % parameter)

                data_to_change = data[error_introduction_location +
                                      1:error_introduction_location+1+(2*parameter)]

                changed_data = data_to_change[parameter:] + \
                    data_to_change[:parameter]

                new_data = data[:error_introduction_location+1] + \
                    changed_data + \
                    data[error_introduction_location+1+(2*parameter):]

        elif method == "crc":

            crc_polynomial_hex = parameter[2:]
            error_pattern = bytes.fromhex(crc_polynomial_hex)
            parameter_length = len(error_pattern)

            if len(data) >= error_introduction_location+1+parameter_length:

                error_introduction_location = error_introduction_location - \
                    (error_introduction_location % parameter_length)

                data_to_change = data[error_introduction_location +
                                      1:error_introduction_location+1+parameter_length]

                changed_data = bytes([data_to_change[i] ^ error_pattern[i]
                                      for i in range(parameter_length)])

                new_data = data[:error_introduction_location+1] + \
                    changed_data + \
                    data[error_introduction_location+1+parameter_length:]

        return new_data
