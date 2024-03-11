import json
import struct
from multiprocessing import shared_memory

from abst.config import max_json_shared


class LocalBroadcast:
    _instance = None

    def __new__(cls, name: str, size: int = max_json_shared):
        if cls._instance is None:
            cls._instance = super(LocalBroadcast, cls).__new__(cls)
            cls._instance._init_shared_memory(name, size)
        return cls._instance

    def _init_shared_memory(self, name: str, size: int):
        self.data_name = name
        self.len_name = f"{name}_len"
        self.size = size

        try:
            # Attempt to create the main shared memory block
            self.data_shm = shared_memory.SharedMemory(name=self.data_name, create=True, size=size)
            self.data_is_owner = True
        except FileExistsError:
            self.data_shm = shared_memory.SharedMemory(name=self.data_name, create=False)
            self.data_is_owner = False

        try:
            # Attempt to create the shared memory block for data length
            self.len_shm = shared_memory.SharedMemory(name=self.len_name, create=True, size=8)
            self.len_is_owner = True
        except FileExistsError:
            self.len_shm = shared_memory.SharedMemory(name=self.len_name, create=False)
            self.len_is_owner = False

    def store_json(self, data: dict) -> int:
        """
        Serialize and store JSON data in shared memory.
        @return: Size of the serialized data in bytes
        """
        serialized_data = json.dumps(data).encode('utf-8')
        if len(serialized_data) > self.size:
            raise ValueError("Data exceeds allocated shared memory size.")

        # Write the data length to the length shared memory
        self.len_shm.buf[:8] = struct.pack('Q', len(serialized_data))

        # Write data to the main shared memory
        self.data_shm.buf[:len(serialized_data)] = serialized_data
        return len(serialized_data)

    def retrieve_json(self) -> dict:
        """
        Retrieve and deserialize JSON data from shared memory.
        """
        # Read the data length from the length shared memory
        data_length = self.get_data_length()

        # Read data from the main shared memory
        data = bytes(self.data_shm.buf[:data_length]).decode('utf-8')
        return json.loads(data)

    def get_data_length(self):
        return struct.unpack('Q', self.len_shm.buf[:8])[0]

    def close(self):
        """Close and unlink the shared memory blocks."""
        self.data_shm.close()
        self.len_shm.close()
        if self.data_is_owner:
            self.data_shm.unlink()
        if self.len_is_owner:
            self.len_shm.unlink()
