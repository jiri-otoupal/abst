import click
import rich
from InquirerPy import inquirer

from abst.bastion_support.bastion_scheduler import BastionScheduler
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


@parallel.command("add", help="Add Bastion to stack")
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default="default")
def add(debug, context_name):
    """
    Add Bastions to stack

    use default for adding default cluster ! this is reserved name !
    :param debug:
    :param context_name:
    :return:
    """
    setup_calls(debug)

    BastionScheduler.add_bastion(context_name)
    display_scheduled()


@parallel.command("remove", help="Remove Bastion from stack")
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default="default")
def remove(debug, context_name):
    setup_calls(debug)
    BastionScheduler.remove_bastion(context_name)
    display_scheduled()


@parallel.command("run", help="Run All Bastions in fullauto")
@click.option("--debug", is_flag=True, default=False)
@click.option("-y", is_flag=True, default=False, help="Automatically confirm")
@click.option("-f", "--force", is_flag=True, default=False, help="Will force connections ignoring security policies")
def run(debug, y, force):
    setup_calls(debug)
    if force:
        rich.print("[red]Running in force mode[/red][gray] this mode is less secure as it is ignoring key checking and"
                   " security policies involving known_hosts[/gray]")
    display_scheduled()
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
    BastionScheduler.run(force)


@parallel.command("display", help="Display current Bastions is stack")
@click.option("--debug", is_flag=True, default=False)
def display(debug):
    setup_calls(debug)

    display_scheduled()
