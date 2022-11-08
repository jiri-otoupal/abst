from pathlib import Path

default_conf_path: Path = (Path().home().resolve() / ".abst" / "config.json")
default_creds_path: Path = (Path().home().resolve() / ".abst" / "creds.json")
default_config_keys = (
    "host", "bastion-id", "default-name", "ssh-pub-path", "private-key-path", "target-ip",
    "local-port", "target-port", "ttl", "resource-id", "resource-os-username",
    "private-key-path")
default_contexts_location: Path = (Path().home().resolve() / ".abst" / "contexts")

default_conf_contents = {"used_context": None}
