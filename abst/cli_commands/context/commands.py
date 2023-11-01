import logging
from pathlib import Path

import click
import pyperclip
import rich

from abst.config import default_contexts_location, share_excluded_keys
from abst.utils.misc_funcs import get_context_data, setup_calls


@click.group(help="Contexts commands")
def context():
    pass


@context.command("list", help="Will list all contexts in ~/.abst/context/ folder")
@click.option("--debug", is_flag=True, default=False)
def _list(debug=False):
    setup_calls(debug)
    rich.print("Contexts:")
    for file in Path(default_contexts_location).iterdir():
        rich.print(f"    {file.name.replace('.json', '')}")


@context.command(help="Will display JSON format of context")
@click.option("--debug", is_flag=True, default=False)
@click.argument("name")
def display(name, debug=False):
    setup_calls(debug)
    data = get_context_data(name)
    if data is None:
        return
    rich.print_json(data=data)


@context.command(help="Will print context without local paths and put it in clipboard for sharing")
@click.option("--debug", is_flag=True, default=False)
@click.argument("name")
def share(name, debug=False):
    setup_calls(debug)

    data = get_context_data(name)
    if data is None:
        return
    for key in share_excluded_keys:
        data.pop(key)
    data["default-name"] = "!YOUR NAME!"
    rich.print_json(data=data)
    logging.info("Data transmitted into clipboard")
    pyperclip.copy(str(data))
