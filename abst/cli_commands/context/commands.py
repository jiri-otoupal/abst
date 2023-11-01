import json
from pathlib import Path

import click
import rich

from abst.config import default_contexts_location


@click.group(help="Contexts commands")
def context():
    pass


@context.command("list", help="Will list all contexts in ~/.abst/context/ folder")
def _list():
    rich.print("Contexts:")
    for file in Path(default_contexts_location).iterdir():
        rich.print(f"    {file.name.replace('.json', '')}")


@context.command(help="Will display JSON format of context")
@click.argument("name")
def display(name):
    if name in [file.name.replace(".json", "") for file in
                Path(default_contexts_location).iterdir()]:
        rich.print("[bold]Context config contents:[/bold]\n")
        with open(Path(default_contexts_location) / (name + ".json"), "r") as f:
            rich.print_json(data=json.load(f))
    else:
        rich.print("[red]Context does not exists[/red]")
