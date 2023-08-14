from crc import CRC
from checksum import Checksum
from header import Header, fixed_format
from packet import Packet
import struct


class SendReceive:

    def get_value_to_check(chunk, method, parameter):
        if method == "crc":
            crc_obj = CRC(parameter)
            value = crc_obj.calculate(chunk)
        elif method == "checksum":
            checksum_obj = Checksum(parameter)
            value = checksum_obj.calculate(chunk)
        return value

    def send_data(chunk, sending_socket, buffer, seq_num, src, dest, size_of_chunk, ack_byte, errors, error_detection_method, parameter):
        while not buffer.is_full():
            check_value = super().get_value_to_check(
                chunk, error_detection_method, parameter)
            header = Header(seq_num, src, dest, check_value, size_of_chunk,
                            ack_byte, errors)
            packed_header = header.pack()
            packet = Packet(packed_header, chunk)
            buffer.add(packet)
            sending_socket.sendall(packed_header)
            sending_socket.send(header.check_value.encode())
            sending_socket.sendall(struct.pack(
                f"{header.size_of_errors}i", *header.errors))

            sending_socket.sendall(chunk)

    def receive_data(self, receiving_sock):
        fixed_data = receiving_sock.recv(struct.calcsize(fixed_format))
        received_seq_num, received_src, received_dest, received_size_of_check_value, received_size_of_chunk, received_ack_byte, received_size_of_errors = struct.unpack(
            fixed_format, fixed_data)

        received_check_value = receiving_sock.recv(
            received_size_of_check_value).decode()

        received_errors_format = f"{received_size_of_errors}i"
        received_errors_data = receiving_sock.recv(
            struct.calcsize(received_errors_format))
        received_errors = list(struct.unpack(
            received_errors_format, received_errors_data))
        received_chunk = receiving_sock.recv(received_size_of_chunk).decode()

        return received_seq_num, received_src, received_dest, received_check_value, received_chunk, received_ack_byte, received_errors

        # if dest.decode() != client_name:
        #     data_to_forward = fixed_data + check_value.encode() + errors_data
        #     seq_num = 0
        #     while data_to_forward:
        #         seq_num += 1
        #         seq_num %= (2*window_size)
        #         chunk = data_to_forward[:chunk_size]
        #         data_to_forward = data_to_forward[chunk_size:]

        #         new_check_value = super().get_value_to_check(
        #             chunk, error_detection_method, parameter)
        #         new_errors = []
        #         self.send_data(chunk, sending_socket, buffer, seq_num, client_name, new_dest, new_check_value, len(chunk),
        #                        0, new_errors)
        #     else:
