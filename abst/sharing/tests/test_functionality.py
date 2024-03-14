import unittest

from abst.sharing.local_broadcast import LocalBroadcast


class TestLocalBroadcast(unittest.TestCase):
    lb = None
    shared_memory_size = None
    shared_memory_name = None

    @classmethod
    def setUpClass(cls):
        # Use unique names for each test run to avoid conflicts
        cls.shared_memory_name = 'test_shared_memory'
        cls.shared_memory_size = 1024
        cls.lb = LocalBroadcast(cls.shared_memory_name, cls.shared_memory_size)

    @classmethod
    def tearDownClass(cls):
        # Cleanup shared memory
        cls.lb.close()

    def test_store_and_retrieve_json(self):
        test_data = {'key': 'value', 'integer': 42, 'float': 3.14, 'list': [1, 2, 3]}
        self.lb.store_json("test", test_data)
        retrieved_data = self.lb.retrieve_json("test")
        self.assertEqual(test_data, retrieved_data)

    def test_data_length_persistence(self):
        # This test ensures that the data length is correctly stored and retrieved,
        # implying it's shared correctly across instances/processes
        initial_data = {'key': 'initial'}
        size = self.lb.store_json(initial_data)

        # Create a new LocalBroadcast instance to mimic another process
        new_instance = LocalBroadcast(self.shared_memory_name, self.shared_memory_size)
        self.assertEqual(size, new_instance.get_used_space())
        initial_data_retrieved = new_instance.retrieve_json()
        self.assertEqual(initial_data, initial_data_retrieved)

        # Now store new data and verify the updated length is respected
        updated_data = {'key': 'updated', 'more': [1, 2, 3]}
        self.lb.store_json(updated_data)
        updated_data_retrieved = new_instance.retrieve_json()
        self.assertEqual(updated_data, updated_data_retrieved)

    def test_previous_data_not_overwritten(self):
        # Create a new LocalBroadcast instance to mimic another process
        new_instance_a = LocalBroadcast(self.shared_memory_name, self.shared_memory_size)
        new_instance_a.store_json({"Britney": "Hey"})
        new_instance_b = LocalBroadcast(self.shared_memory_name, self.shared_memory_size)
        new_instance_b.store_json({"Katty": "Whassup"})
        self.assertEqual(new_instance_b.retrieve_json(), {"Britney": "Hey", "Katty": "Whassup"})

    def test_previous_data_not_overwritten_same_key(self):
        # Create a new LocalBroadcast instance to mimic another process
        new_instance_a = LocalBroadcast(self.shared_memory_name, self.shared_memory_size)
        new_instance_a.store_json({"Britney": {"Katty": "Whassup"}})
        new_instance_b = LocalBroadcast(self.shared_memory_name, self.shared_memory_size)
        new_instance_b.store_json({"Britney": {"Chris": "Heey"}})
        self.assertEqual(new_instance_b.retrieve_json(), {"Britney": {"Katty": "Whassup", "Chris": "Heey"}})

    def test_exceed_memory_size(self):
        # This test verifies that an error is raised when trying to store data
        # that exceeds the allocated shared memory size
        large_data = {'key': 'x' * 2000}  # Assuming this exceeds the shared memory size
        with self.assertRaises(ValueError):
            self.lb.store_json(large_data)


if __name__ == '__main__':
    unittest.main()
