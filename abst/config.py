from pathlib import Path

default_stack_location: Path = (Path().home().resolve() / ".abst" / "stack.json")
default_conf_path: Path = (Path().home().resolve() / ".abst" / "config.json")
default_creds_path: Path = (Path().home().resolve() / ".abst" / "creds.json")
default_config_keys: tuple = (
    "host", "bastion-id", "default-name", "ssh-pub-path", "private-key-path", "target-ip",
    "local-port", "target-port", "ttl", "resource-id", "resource-os-username",
    "private-key-path")
default_contexts_location: Path = (Path().home().resolve() / ".abst" / "contexts")
default_stack_contents: dict = {"stack": []}
default_conf_contents: dict = {"used_context": None}


def get_public_key(ssh_path):
    with open(ssh_path, "r") as f:
        return f.read()
