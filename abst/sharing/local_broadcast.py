import json
import struct
from json import JSONDecodeError
from multiprocessing import shared_memory

from deepmerge import always_merger

from abst.config import max_json_shared


class LocalBroadcast:
    _instance = None

    def __new__(cls, name: str, size: int = max_json_shared):
        if cls._instance is None:
            cls._instance = super(LocalBroadcast, cls).__new__(cls)
            cls._instance.__init_shared_memory(name[:14], size)
        return cls._instance

    def __init_shared_memory(self, name: str, size: int):
        self._data_name = name
        self._len_name = f"{name}_len"
        self._size = size

        try:
            # Attempt to create the main shared memory block
            self._data_shm = shared_memory.SharedMemory(name=self._data_name, create=True, size=size)
            self._data_is_owner = True
        except FileExistsError:
            self._data_shm = shared_memory.SharedMemory(name=self._data_name, create=False)
            self._data_is_owner = False

        try:
            self._len_shm = shared_memory.SharedMemory(name=self._len_name, create=True, size=8)
            self._len_shm.buf[:8] = struct.pack('Q', 0)
            self._len_is_owner = True
        except FileExistsError:
            self._len_shm = shared_memory.SharedMemory(name=self._len_name, create=False)
            self._len_is_owner = False

    def store_json(self, data: dict) -> int:
        """
        Serialize and store JSON data in shared memory.
        @return: Size of the serialized data in bytes
        """

        data_before = self.retrieve_json()
        for key, value in data.items():
            for s_key in value.keys():
                if data_before.get(key, None) is not None and data_before.get(key, None).get(s_key,
                                                                                             None) is not None and type(
                    data_before[key][s_key]) == type(data[key][s_key]):
                    data_before[key].pop(s_key)

        data_copy = always_merger.merge(data, data_before)

        serialized_data = self.__write_json(data_copy)
        return len(serialized_data)

    def __write_json(self, data: dict):
        serialized_data = json.dumps(data).encode('utf-8')
        if len(serialized_data) > self._size:
            raise ValueError("Data exceeds allocated shared memory size.")
        # Write the data length to the length shared memory
        self._len_shm.buf[:8] = struct.pack('Q', len(serialized_data))
        # Write data to the main shared memory
        self._data_shm.buf[:len(serialized_data)] = serialized_data
        return serialized_data

    def delete_context(self, context: str):
        data_before = self.retrieve_json()
        data_before.pop(context, None)
        self.__write_json(data_before)

    def retrieve_json(self) -> dict:
        """
        Retrieve and deserialize JSON data from shared memory.
        """
        # Read the data length from the length shared memory
        data_length = self.get_used_space()

        if data_length == -1:
            return {}

        # Read data from the main shared memory
        data = bytes(self._data_shm.buf[:data_length]).decode('utf-8')
        try:
            return json.loads(data)
        except JSONDecodeError:
            return {}

    def get_used_space(self) -> int:
        """
        Get the size of the shared memory
        @return: Number of bytes used
        """
        if self._len_shm.buf is None:
            return -1
        return struct.unpack('Q', self._len_shm.buf[:8])[0]

    def close(self):
        """Close and unlink the shared memory blocks."""
        try:
            self._data_shm.close()
            self._len_shm.close()
            if self._data_is_owner:
                self._data_shm.unlink()
            if self._len_is_owner:
                self._len_shm.unlink()
        except FileNotFoundError:
            pass
