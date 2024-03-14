import json

from deepmerge import always_merger

from abst.config import default_shared_mem_path


class LocalBroadcast:
    _instance = None
    _base_dir = default_shared_mem_path

    def __new__(cls, name: str):
        if cls._instance is None:
            cls._instance = super(LocalBroadcast, cls).__new__(cls)
            cls._instance.__init_files(name)
        return cls._instance

    def __init_files(self, name: str):
        self._base_name = name
        # Ensure base directory exists
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, context):
        # Generates a file path for a given context using a Path object
        return self._base_dir / f"{self._base_name}_{context}.json"

    def store_json(self, context: str, data: dict) -> int:
        """
        Serialize and store JSON data in a file named by context.
        @return: Size of the serialized data in bytes
        """
        file_path = self._get_file_path(context)
        data_before = self.retrieve_json(context)

        # Merge new data with existing data
        for s_key in list(data_before.keys()):
            if data_before.get(s_key, None) is not None and type(
                    data_before[s_key]) == type(data.get(s_key, None)):
                data_before.pop(s_key)
        data_merged = always_merger.merge(data_before, data)

        with file_path.open('w', encoding='utf-8') as file:
            json.dump(data_merged, file)

        return file_path.stat().st_size

    def delete_context(self, context: str):
        file_path = self._get_file_path(context)
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass  # Context file already deleted or never existed

    def retrieve_json(self, context: str) -> dict:
        """
        Retrieve and deserialize JSON data from a file named by context.
        """
        file_path = self._get_file_path(context)
        if not file_path.exists():
            return {}

        with file_path.open('r', encoding='utf-8') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                print(f"Failed to load JSON from {file_path}: {e}")
                return {}

    def list_contents(self) -> dict:
        """
        List files in the base directory and return a dictionary where file names
        are keys and the values are the contents of the files.
        """
        content_dict = {}
        for file_path in self._base_dir.iterdir():
            if file_path.is_file() and file_path.suffix == '.json':
                # Extract the context from the file name
                context = file_path.stem.replace(f"{self._base_name}_", "")
                content_dict[context] = self.retrieve_json(context)
        return content_dict
