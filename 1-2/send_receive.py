from crc import CRC
from checksum import Checksum


class SendReceive:

    def get_value_to_check(chunk, method, polynomial=None, bytes_length=None):
        if method == "crc":
            crc_obj = CRC(polynomial)
            value = crc_obj.calculate(chunk)
            # value_bytes = int(value, 2).to_bytes(len(value) // 8, 'big')
        elif method == "checksum":

            checksum_obj = Checksum(bytes_length)
            value = checksum_obj.calculate(chunk)

        return value
