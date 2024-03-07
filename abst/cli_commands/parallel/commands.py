import click
import rich
from InquirerPy import inquirer
from rich.tree import Tree

from abst.bastion_support.bastion_scheduler import BastionScheduler
from abst.bastion_support.oci_bastion import Bastion
from abst.config import default_parallel_sets_location
from abst.tools import display_scheduled
from abst.utils.misc_funcs import setup_calls


@click.group(help="Parallel Bastion Control group")
def parallel():
    """
    Only Port Forwarded sessions are supported

    This makes it possible to run multiple forward sessions of multiple context in
     the same time, useful when working with multiple clusters
    """
    pass


@click.group(help="Alias for Parallel Bastion Control group")
def pl():
    """
    Only Port Forwarded sessions are supported

    This makes it possible to run multiple forward sessions of multiple context in
     the same time, useful when working with multiple clusters
    """
    pass


@parallel.command("add", help="Add Bastion to stack")
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default="default")
def add(debug, context_name):
    """
    Add Bastions to stack

    use default for adding default cluster ! this is reserved name!
    :param debug:
    :param context_name:
    :return:
    """
    setup_calls(debug)

    BastionScheduler.add_bastion(context_name)
    display_scheduled()


@parallel.command("create", help="Create folder for a parallel set")
@click.option("--debug", is_flag=True, default=False)
@click.argument("set-name", default="default")
def create(debug, set_name):
    """
    Create folder for a parallel set

    :param debug:
    :param set_name:
    :return:
    """
    setup_calls(debug)
    try:
        set_dir = default_parallel_sets_location / set_name
        set_dir.mkdir()
        rich.print(f"[green]Set {set_name} created![/green]")
        rich.print(
            f"Feel free to copy any context to {set_dir} for it to be run in [yellow]{set_name}[/yellow] parallel set")
        rich.print(f"You can run this set by 'abst parallel run {set_name}'")
    except OSError:
        rich.print("[red]Set already exists[/red]")


@parallel.command("list", help="List folder of a parallel set")
@click.option("--debug", is_flag=True, default=False)
def _list(debug):
    setup_calls(debug)
    tree = Tree("Sets in parallel folder")

    for _set in default_parallel_sets_location.iterdir():
        if _set.name.startswith("."):
            continue
        leaf = tree.add(f"{_set.name.replace('.json', '')}")
        for ctx in _set.iterdir():
            if ctx.name.startswith(".") or not ctx.name.endswith(".json"):
                continue
            cfg = Bastion.load_json(ctx)
            used_time = "" if "last-time-used" not in cfg.keys() else f"| last time used {cfg['last-time-used']}"
            if ctx.name.startswith(".") or not ctx.name.endswith(".json"):
                continue
            leaf.add(f"{ctx.name.replace('.json', '')} {used_time}")

    if not len(tree.children):
        rich.print("No contexts")

    rich.print(tree)


@parallel.command("remove", help="Remove Bastion from stack (Can not remove sets)")
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default="default")
def remove(debug, context_name):
    setup_calls(debug)
    BastionScheduler.remove_bastion(context_name)
    display_scheduled()


@parallel.command("run", help="Run All Bastions in fullauto")
@click.option("--debug", is_flag=True, default=False)
@click.option("-y", is_flag=True, default=False, help="Automatically confirm")
@click.option("-f", "--force", is_flag=True, default=False,
              help="Will force connections ignoring security policies")
@click.argument("set_name", default=None, required=False, type=str)
def run(debug, y, force, set_name=None):
    setup_calls(debug)
    if force:
        rich.print(
            "[red]Running in force mode[/red][gray] this mode is less secure as it is ignoring key checking and"
            " security policies involving known_hosts[/gray]")
    if set_name:
        set_dir = get_set_dir(set_name)
    else:
        set_dir = None

    display_scheduled(set_dir)
    if not y:
        try:
            confirm = inquirer.confirm(
                "Do you really want to run following contexts?"
            ).execute()
        except KeyError:
            rich.print("Unknown inquirer error, continuing...")
            confirm = True
        if not confirm:
            rich.print("[green]Cancelling, nothing started[/green]")
            exit(0)
    BastionScheduler.run(force, set_dir)


def get_set_dir(set_name):
    set_dir = default_parallel_sets_location / set_name
    if not set_dir.exists():
        rich.print(f"Parallel set {set_name} did not found in {set_dir}")
        exit(1)
    elif len(list(set_dir.iterdir())) == 0:
        rich.print(f"[red]No contexts found in {set_dir}[/red]")
        exit(1)
    return set_dir


@parallel.command("display", help="Display current Bastions is stack")
@click.option("--debug", is_flag=True, default=False)
@click.argument("set_name", default=None, required=False, type=str)
def display(debug, set_name):
    setup_calls(debug)
    if set_name:
        set_dir = get_set_dir(set_name)
    else:
        set_dir = None
    display_scheduled(set_dir)


pl.add_command(add)
pl.add_command(create)
pl.add_command(_list, name="list")
pl.add_command(remove)
pl.add_command(run)
pl.add_command(display)
