from pathlib import Path

# Default config
default_shared_mem_path: Path = (Path().home().resolve() / ".abst" / "shared_mem")
default_stack_location: Path = (Path().home().resolve() / ".abst" / "stack.json")
default_conf_path: Path = (Path().home().resolve() / ".abst" / "config.json")
default_creds_path: Path = (Path().home().resolve() / ".abst" / "creds.json")
default_contexts_location: Path = (Path().home().resolve() / ".abst" / "contexts")
default_parallel_sets_location: Path = (Path().home().resolve() / ".abst" / "sets")

default_context_keys: tuple = (
    "host", "bastion-id", "default-name", "ssh-pub-path", "private-key-path", "target-ip",
    "local-port", "target-port", "ttl", "resource-id", "resource-os-username", "region",
    "ssh-custom-arguments")
default_stack_contents: dict = {"stack": []}
default_conf_contents: dict = {"used_context": None, "private-key-path": "~/.ssh/id_rsa",
                               "ssh-pub-path": "~/.ssh/id_rsa"
                                               ".pub"}

# Share Config
share_excluded_keys: tuple = ("private-key-path", "ssh-pub-path", "last-time-used")

# Max Shared JSON size
max_json_shared = 1048576  # Bytes
broadcast_shm_name = "abst_shared_memory"


def get_public_key(ssh_path):
    with open(str(Path(ssh_path).expanduser().resolve()), "r") as f:
        return f.read()
