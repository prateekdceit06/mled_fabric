class Checksum:
    def __init__(self, checksum_length):
        self.checksum_length = int(checksum_length)

    def calculate(self, input_data):
        sum_val = 0
        for i in range(0, len(input_data), self.checksum_length):
            segment_end = min(i + self.checksum_length, len(input_data))
            sum_val += self.byte_array_to_int(input_data, i, segment_end)
        checksum = ~sum_val
        return str(checksum)

    def verify(self, input_data, value_to_compare):
        calculated_checksum = self.calculate(input_data)
        return calculated_checksum == value_to_compare

    @staticmethod
    def byte_array_to_int(bytes_data, start, end):
        value = 0
        for i in range(start, start + end - start):
            value = (value << 8) + (bytes_data[i] & 0xff)
        return value

    def __str__(self):
        return f"Checksum length: {self.checksum_length}"

# Example usage:
# checksum = Checksum(2)
# data = bytearray([1, 2, 3, 4, 5, 6])
# print(checksum.calculate(data))
# print(checksum.verify(data, checksum.calculate(data)))
