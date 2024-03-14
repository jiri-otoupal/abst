from time import sleep

import click
import rich

from abst.bastion_support.oci_bastion import Bastion
from abst.utils.misc_funcs import setup_calls, print_eligible, link_bastion_signals


@click.group(help="Group of commands for creating Bastion sessions")
def create():
    pass


@click.group(name="do", help="Alias Group of commands for creating Bastion sessions")
def _do():
    pass


@create.command(
    "forward",
    help="Creates and connects to Bastion session indefinitely until terminated by user",
)
@click.option("--shell", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def forward(shell, debug, context_name):
    """Creates and connects to bastion sessions
    automatically until terminated"""

    setup_calls(debug)

    if context_name == "?":
        print_eligible("required only for Port Forward session")
        return

    if context_name is None:
        conf = Bastion.load_config()
        used_name = conf["used_context"]
    else:
        used_name = context_name

    bastion = None
    try:
        while True:
            creds = Bastion.get_creds_path_resolve(context_name)
            bastion = Bastion(used_name, region=Bastion.load_json(creds).get("region", None))
            link_bastion_signals(bastion)
            bastion.create_forward_loop(shell=shell)
            sleep(1)
    except FileNotFoundError:
        rich.print("[red]No such context found[/red]")
    except KeyboardInterrupt:
        bastion.kill()


@create.command(
    "managed",
    help="Creates and connects to Bastion session indefinitely until terminated by user",
)
@click.option("--shell", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def managed(shell, debug, context_name):
    """Creates and connects to bastion sessions
    automatically until terminated"""
    setup_calls(debug)

    if context_name == "?":
        print_eligible("required only for Managed SSH session")
        return

    if context_name is None:
        conf = Bastion.load_config()
        used_name = conf["used_context"]
    else:
        used_name = context_name

    bastion = True
    try:
        while type(bastion) == bool or not bastion.stopped:
            creds = Bastion.get_creds_path_resolve(context_name)
            bastion = Bastion(used_name, region=Bastion.load_json(creds).get("region", None))
            link_bastion_signals(bastion)
            bastion.create_managed_loop(shell=shell)

            sleep(1)
    except FileNotFoundError:
        rich.print("[red]No such context found[/red]")
    except KeyboardInterrupt:
        bastion.kill()
        exit(0)

_do.add_command(forward)
_do.add_command(managed)
