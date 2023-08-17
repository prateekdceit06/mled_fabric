import threading


class CircularBuffer:
    def __init__(self, size):
        self.buffer = [None] * size
        self.head = 0
        self.tail = 0
        self.count = 0  # Add a count variable to keep track of the number of elements
        self.lock = threading.Lock()

    def add(self, packet):
        with self.lock:
            self.buffer[self.tail] = packet
            self.tail = (self.tail + 1) % len(self.buffer)
            self.count += 1

    def remove(self):
        with self.lock:
            self.head = (self.head + 1) % len(self.buffer)
            self.count -= 1

    def get(self):
        with self.lock:
            return self.buffer[self.head]

    def get_by_sequence(self, sequence_number):
        with self.lock:
            for packet in self.buffer:
                if packet and packet.seq_num == sequence_number:
                    return packet
            return None

    def remove_by_sequence(self, sequence_number):
        with self.lock:
            for i in range(len(self.buffer)):
                packet = self.buffer[i]
                if packet and packet.seq_num == sequence_number:
                    # Remove the packet and shift elements
                    self.buffer = self.buffer[:i] + self.buffer[i+1:] + [None]
                    if i == self.tail:
                        self.tail = (self.tail - 1) % len(self.buffer)

                    if i < self.head:
                        self.head -= 1
                    self.count -= 1
                    break
            return packet

    def is_full(self):
        with self.lock:
            return self.count == len(self.buffer)

    def is_empty(self):
        with self.lock:
            return self.count == 0

    def print_buffer(self):
        buffer_str = ""
        with self.lock:
            for i in range(len(self.buffer)):
                packet = self.buffer[i]
                if packet:
                    buffer_str += f" <Position {i}>: <Seq Num {packet.seq_num}> "
                else:
                    buffer_str += f"<Position {i}>: <None> "
        return buffer_str
