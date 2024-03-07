import json
import logging
from json import JSONDecodeError
from pathlib import Path

import click
import pyperclip
import rich
from InquirerPy import inquirer
from rich.tree import Tree

from abst.bastion_support.oci_bastion import Bastion
from abst.cfg_func import __upgrade
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

    tree = Tree("Contexts")

    for file in Path(default_contexts_location).iterdir():
        if file.name.startswith(".") or not file.name.endswith(".json"):
            continue
        cfg = Bastion.load_json(file)
        used_time = "" if "last-time-used" not in cfg.keys() else f"| Used: {cfg['last-time-used']}"
        tree.add(f"{file.name.replace('.json', '')} {used_time}")

    if not len(tree.children):
        rich.print("No contexts")

    rich.print(tree)


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
    help="Will share context without local paths and put it in clipboard for sharing")
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


@context.command("generate", help="Will generate sample json and overwrite changes")
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def generate(debug, context_name):
    setup_calls(debug)

    path = get_context_path(context_name)

    Bastion.create_default_locations()
    td = Bastion.generate_sample_dict()
    creds_path = Bastion.write_creds_json(td, path)
    print(
        f"Sample credentials generated, please fill 'creds.json' in {creds_path} with "
        f"your credentials for this to work, you can use 'abst json fill "
        f"{context_name if context_name else ''}'"
    )


@context.command(
    "fill", help="Fills Json config with credentials you enter interactively"
)
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def fill(debug, context_name):
    setup_calls(debug)

    path = get_context_path(context_name)

    if not path.exists():
        rich.print("Generating sample Creds file")
        Bastion.create_default_locations()
        td = Bastion.generate_sample_dict()
        Bastion.write_creds_json(td, path)

    if not default_contexts_location.exists():
        rich.print("Generating contexts location")
        Bastion.create_default_locations()

    rich.print(f"[green]Filling {str(path)}")
    rich.print("Please fill field one by one as displayed")
    n_dict = dict()

    creds_json_ro = Bastion.load_json(path)

    for key, value in creds_json_ro.items():
        n_dict[key] = inquirer.text(
            message=f"{key.capitalize()}:", default=value
        ).execute()
    rich.print("\n[red]New json looks like this:[/red]")
    rich.print_json(data=n_dict)
    if inquirer.confirm(message="Write New Json ?", default=False).execute():
        Bastion.write_creds_json(n_dict, path)
        rich.print("[green]Wrote changes[/green]")
    else:
        rich.print("[red]Fill interrupted, nothing changed[/red]")


@context.command(
    "locate", help="Locates Json config with credentials you enter interactively"
)
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def locate(debug, context_name):
    setup_calls(debug)

    path = get_context_path(context_name)

    if path.exists():
        rich.print(f"[green]Config file location: {path.absolute()}[/green]")
    else:
        rich.print(
            f"[red]Config does not exist yet, future location"
            f" {path.absolute()}[/red]"
        )


@context.command(
    "upgrade", help="Upgrades Json config with credentials you enter interactively"
)
@click.option("--debug", is_flag=True, default=False)
@click.option("--all", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def upgrade(debug, context_name, all):
    setup_calls(debug)

    path = get_context_path(context_name)

    if not path.exists():
        rich.print("[green]No config to upgrade[/green]")
        return

    __upgrade(context_name, path, all)


ctx.add_command(_list, "list")
ctx.add_command(display, "display")
ctx.add_command(share, "share")
ctx.add_command(paste, "paste")
ctx.add_command(generate, "generate")
ctx.add_command(fill, "fill")
ctx.add_command(locate, "locate")
ctx.add_command(upgrade, "upgrade")
