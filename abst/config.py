from pathlib import Path

# Default config
default_stack_location: Path = (Path().home().resolve() / ".abst" / "stack.json")
default_conf_path: Path = (Path().home().resolve() / ".abst" / "config.json")
default_creds_path: Path = (Path().home().resolve() / ".abst" / "creds.json")
default_config_keys: tuple = (
    "host", "bastion-id", "default-name", "ssh-pub-path", "private-key-path", "target-ip",
    "local-port", "target-port", "ttl", "resource-id", "resource-os-username", "region")
default_contexts_location: Path = (Path().home().resolve() / ".abst" / "contexts")
default_stack_contents: dict = {"stack": []}
default_conf_contents: dict = {"used_context": None, "private-key-path": "~/.ssh/id_rsa",
                               "ssh-pub-path": "~/.ssh/id_rsa"
                                               ".pub"}

# Share Config
share_excluded_keys: tuple = ("private-key-path", "ssh-pub-path")


def get_public_key(ssh_path):
    with open(str(Path(ssh_path).expanduser().resolve()), "r") as f:
        return f.read()
