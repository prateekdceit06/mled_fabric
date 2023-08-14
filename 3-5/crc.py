class CRC:
    def __init__(self, crc_polynomial_hex):
        self.crc_polynomial_hex = crc_polynomial_hex
        self.crc_polynomial_binary = self.hex_to_bin(crc_polynomial_hex)

    def calculate(self, input_bytes):
        binary_string = self.byte_array_to_string(
            input_bytes) + self.get_zeros(len(self.crc_polynomial_binary) - 1)
        remainder = self.divide(binary_string, self.crc_polynomial_binary)
        return remainder

    def verify(self, input_bytes, value_to_compare):
        binary_string = self.byte_array_to_string(
            input_bytes) + value_to_compare
        remainder = self.divide(binary_string, self.crc_polynomial_binary)
        zeros = self.get_zeros(len(self.crc_polynomial_binary) - 1)
        return remainder == zeros

    @staticmethod
    def hex_to_bin(hex_val):
        bin_val = bin(int(hex_val, 16))[2:]
        return bin_val

    @staticmethod
    def get_zeros(n):
        return '0' * n

    def divide(self, dividend, divisor):
        pointer = len(divisor)
        remainder = dividend[:pointer]
        result = remainder

        while pointer < len(dividend):
            if remainder[0] == '1':
                remainder = self.xor(remainder, divisor) + dividend[pointer]
            else:
                remainder = self.xor(remainder, self.get_zeros(
                    len(divisor))) + dividend[pointer]

            remainder = remainder[1:]
            pointer += 1

        if remainder[0] == '1':
            remainder = self.xor(remainder, divisor)
        else:
            remainder = self.xor(remainder, self.get_zeros(len(divisor)))

        return remainder[1:]

    @staticmethod
    def xor(a, b):
        return ''.join('0' if a[i] == b[i] else '1' for i in range(len(a)))

    def __str__(self):
        return f"CRC Polynomial: {self.crc_polynomial_hex}, CRC Polynomial in binary: {self.crc_polynomial_binary}."

    @staticmethod
    def byte_array_to_string(byte_array):
        return ''.join(format(byte, '08b') for byte in byte_array)


# Example usage:
# crc = CRC("0x104C11DB7", "CRC-32")
# data = b"Hello, World!"
# print(crc.calculate(data))
# print(crc.verify(data, crc.calculate(data)))
