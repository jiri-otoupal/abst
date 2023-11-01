import logging

import rich
from requests import ConnectTimeout
from rich.logging import RichHandler

from abst.bastion_support.oci_bastion import Bastion
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
