import json
import logging
from json import JSONDecodeError
from pathlib import Path

import click
import pyperclip
import rich
from InquirerPy import inquirer

from abst.bastion_support.oci_bastion import Bastion
from abst.config import default_contexts_location, share_excluded_keys
from abst.tools import get_context_path
from abst.utils.misc_funcs import get_context_data, setup_calls, get_context_set_data


@click.group(help="Contexts commands")
def context():
    pass


@click.group(help="Context commands alias")
def ctx():
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


@context.command(
    help="Will print context without local paths and put it in clipboard for sharing")
@click.option("--debug", is_flag=True, default=False)
@click.option("--raw", is_flag=True, default=False)
@click.argument("name")
def share(name: str, debug=False, raw=False):
    setup_calls(debug)

    if "/" in name:
        data = get_context_set_data(name)
    else:
        data = get_context_data(name)
    if data is None:
        return

    for key in share_excluded_keys:
        data.pop(key, None)
    data["default-name"] = "!YOUR NAME!"

    if not raw:
        rich.print(f"[bold]Context '{name}' config contents:[/bold]\n")
        logging.debug("Data transmitted into clipboard")
        pyperclip.copy(str(data))
        rich.print("Copied context into clipboard")
    rich.print_json(data=data)


@context.command(help="Will paste context from clipboard into provided context name")
@click.option("--debug", is_flag=True, default=False)
@click.argument("name")
def paste(name, debug=False):
    setup_calls(debug)

    data = pyperclip.paste()
    path = get_context_path(name)
    if data is None:
        return

    try:
        data_loaded = json.loads(data.replace("'", "\""))
    except JSONDecodeError:
        rich.print("[red]Invalid data, please try copying context again[/red]")
        exit(1)

    if data_loaded["default-name"] == "!YOUR NAME!":
        data_loaded["default-name"] = inquirer.text(
            "Please enter your name for bastion session that will be visible in OCI:").execute()

    if inquirer.confirm("Would you like to change IP?").execute():
        data_loaded["target-ip"] = inquirer.text(
            "Please enter your target IP address:").execute()

    if path.exists():
        if not inquirer.confirm("File exists. Overwrite?").execute():
            rich.print("[red]Canceled.[/red]")
            return

    Bastion.write_creds_json(data_loaded, path)
    rich.print(f"Wrote config into '{path}'")


ctx.add_command(_list, "list")
ctx.add_command(display, "display")
ctx.add_command(share, "share")
ctx.add_command(paste, "paste")
