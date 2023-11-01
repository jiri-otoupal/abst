import json
import logging
from pathlib import Path
from typing import Optional

import rich
from requests import ConnectTimeout
from rich.logging import RichHandler

from abst.bastion_support.oci_bastion import Bastion
from abst.config import default_contexts_location
from abst.notifier.version_notifier import Notifier


def setup_calls(debug):
    setup_debug(debug)
    try:
        Notifier.notify()
    except (ConnectionError, ConnectTimeout):
        return False


def setup_debug(debug):
    if not debug:
        logging.disable(logging.DEBUG)
        logging.disable(logging.INFO)

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.CRITICAL,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )


def print_eligible(searched: str):
    contexts = Bastion.get_contexts()
    rich.print("[bold]Configured contexts:[/bold]")
    for key, context in contexts.items():
        do_skip = False
        for value in context.values():
            if searched in value:
                do_skip = True
                break
        if do_skip:
            continue
        rich.print(key)


def get_context_data(name) -> Optional[dict]:
    if name in [file.name.replace(".json", "") for file in
                Path(default_contexts_location).iterdir()]:
        rich.print("[bold]Context config contents:[/bold]\n")
        with open(Path(default_contexts_location) / (name + ".json"), "r") as f:
            data = json.load(f)
            return data
    else:
        rich.print("[red]Context does not exists[/red]")
        return None
