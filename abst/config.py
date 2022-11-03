from pathlib import Path

default_creds_path: Path = (Path().home().resolve() / ".abst" / "creds.json")
default_config_keys = (
    "host", "bastion-id", "default-name", "ssh-pub-path", "private-key-path", "target-ip",
    "local-port", "target-port", "ttl", "resource-id", "resource-os-username",
    "private-key-path")
