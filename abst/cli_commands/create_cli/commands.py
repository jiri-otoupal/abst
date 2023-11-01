from time import sleep

import click

from abst.bastion_support.oci_bastion import Bastion
from abst.utils.misc_funcs import setup_calls, print_eligible


@click.group(help="Group of commands for creating Bastion sessions")
def create():
    pass


@create.command(
    "forward",
    help="Creates and connects to Bastion session indefinitely until terminated by user",
)
@click.option("--shell", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def fullauto_forward(shell, debug, context_name):
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

    while True:
        Bastion(used_name, region=
        Bastion.load_json(Bastion.get_creds_path_resolve(context_name)).get("region",
                                                                            None)).create_forward_loop(
            shell=shell)

        sleep(1)


@create.command(
    "managed",
    help="Creates and connects to Bastion session indefinitely until terminated by user",
)
@click.option("--shell", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def fullauto_managed(shell, debug, context_name):
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

    while True:
        Bastion(used_name, region=
        Bastion.load_json(Bastion.get_creds_path_resolve(context_name)).get("region",
                                                                            None)).create_managed_loop(
            shell=shell)

        sleep(1)
