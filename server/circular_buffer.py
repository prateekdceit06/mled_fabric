import threading


class Packet:
    def __init__(self, sequence_number, data):
        self.sequence_number = sequence_number
        self.data = data


class CircularBuffer:
    def __init__(self, size):
        self.buffer = [None] * size
        self.head = 0
        self.tail = 0
        self.lock = threading.Lock()

    def add(self, packet):
        with self.lock:
            self.buffer[self.tail] = packet
            self.tail = (self.tail + 1) % len(self.buffer)

    def remove(self):
        with self.lock:
            self.head = (self.head + 1) % len(self.buffer)

    def get_chunk(self):
        with self.lock:
            return self.buffer[self.head]

    def get_by_sequence(self, sequence_number):
        with self.lock:
            for packet in self.buffer:
                if packet and packet.sequence_number == sequence_number:
                    return packet
            return None

    def is_full(self):
        with self.lock:
            return (self.tail + 1) % len(self.buffer) == self.head

    def is_empty(self):
        with self.lock:
            return self.head == self.tail
