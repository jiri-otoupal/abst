import logging
import os
import signal
from time import sleep

import click
import rich
from InquirerPy import inquirer
from rich.logging import RichHandler

from abst.config import default_creds_path, default_config_keys
from abst.oci_bastion import Bastion


# Press the green button in the gutter to run the script.
def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()]
    )
    cli()


@click.group()
def cli():
    pass


@cli.group(help="Group of commands for operations with config")
def config():
    pass


@config.command("generate", help="Will generate sample json and overwrite changes")
@click.option("--debug", is_flag=True, default=False)
def generate(debug):
    setup_debug(debug)
    Bastion.create_default_location()
    td = Bastion.generate_sample_dict()
    creds_path = Bastion.write_creds_json(td)
    print(
        f"Sample credentials generated, please fill 'creds.json' in {creds_path} with "
        f"your credentials for this to work, you can use 'abst json fill'")


@config.command("fill", help="Fills Json config with credentials you enter interactively")
@click.option("--debug", is_flag=True, default=False)
def fill(debug):
    setup_debug(debug)

    if not default_creds_path.exists():
        print("Generating sample Creds file")
        Bastion.create_default_location()
        td = Bastion.generate_sample_dict(False)
        Bastion.write_creds_json(td)

    print("Please fill field one by one as displayed")
    n_dict = dict()

    creds_json_ro = Bastion.load_creds_json()
    for key, value in creds_json_ro.items():
        n_dict[key] = inquirer.text(message=f"{key.capitalize()}:",
                                    default=value).execute()
    rich.print("\n[red]New json looks like this:[/red]")
    rich.print_json(data=n_dict)
    if inquirer.confirm(message="Write New Json ?", default=False).execute():
        Bastion.write_creds_json(n_dict)
        rich.print("[green]Wrote changes[/green]")
    else:
        rich.print("[red]Fill interrupted, nothing changed[/red]")


@config.command("locate", help="Locates Json config with credentials you enter interactively")
@click.option("--debug", is_flag=True, default=False)
def locate(debug):
    setup_debug(debug)
    if default_creds_path.exists():
        rich.print(f"[green]Config file location {str(default_creds_path.absolute())}[/green]")
    else:
        rich.print(
            f"[red]Config does not exist yet, future location {str(default_creds_path.absolute())}[/red]")


@config.command("upgrade", help="Locates Json config with credentials you enter interactively")
@click.option("--debug", is_flag=True, default=False)
def upgrade(debug):
    setup_debug(debug)

    if not default_creds_path.exists():
        rich.print("[green]No config to upgrade[/green]")
        return

    creds_json_ro = Bastion.load_creds_json()
    missing_keys = set(default_config_keys).difference(creds_json_ro.keys())

    res_json = dict(creds_json_ro)

    for key in missing_keys:
        res_json[key] = "New Key"

    rich.print_json(data=res_json)
    if inquirer.confirm(message="Write New Json ?", default=False).execute():
        Bastion.write_creds_json(res_json)
        rich.print("[green]Wrote changes[/green]")
    else:
        rich.print("[red]Fill interrupted, nothing changed[/red]")


@cli.command("clean", help="Cleans all credentials created by abst")
def clean():
    """

    """
    s = str(default_creds_path)
    try:
        confirm = inquirer.confirm(
            "Do you really want to Delete all Creds file ? All of credentials will be "
            "lost")
        if not confirm:
            rich.print("[green]Cancelling, nothing changed[/green]")
            exit(0)

        rich.print("[red]Deleting all of the credentials[/red]")

        os.remove(s)
    except PermissionError:
        print("Do not have permission to remove, or process is using this file.")
        print(f"Please delete manually in {s}")


@cli.group(help="Group of commands for creating Bastion sessions")
def create():
    signal.signal(signal.SIGINT, Bastion.kill_bastion)
    signal.signal(signal.SIGTERM, Bastion.kill_bastion)


@create.group(help="Group of commands for Creating Port Forward Sessions")
def forward():
    pass


@create.group(help="Group of commands for Creating Managed SSH Sessions")
def managed():
    pass


@forward.command("single",
                 help="Creates only one bastion session and keeps reconnecting until"
                      " its deleted, does not create any more Bastion sessions")
@click.option("--shell", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
def single(shell, debug):
    """Creates only one bastion session
     ,connects and reconnects until its ttl runs out"""
    setup_debug(debug)

    Bastion.create_forward_loop(shell=shell)


@forward.command("fullauto",
                 help="Creates and connects to Bastion session indefinitely until "
                      "terminated by user")
@click.option("--shell", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
def fullauto(shell, debug):
    """Creates and connects to bastion sessions
     automatically until terminated"""

    setup_debug(debug)

    while True:
        Bastion.create_forward_loop(shell=shell)

        Bastion.connected = False
        Bastion.active_tunnel = None
        Bastion.response = None

        sleep(1)


@managed.command("single",
                 help="Creates only one bastion session and keeps reconnecting until"
                      " its deleted, does not create any more Bastion sessions")
@click.option("--shell", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
def single(shell, debug):
    """Creates only one bastion session
     ,connects and reconnects until its ttl runs out"""
    setup_debug(debug)

    Bastion.create_managed_loop(shell=shell)


def setup_debug(debug):
    if not debug:
        logging.disable(logging.DEBUG)

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.CRITICAL, format="%(message)s", datefmt="[%X]",
        handlers=[RichHandler()]
    )


@managed.command("fullauto",
                 help="Creates and connects to Bastion session indefinitely until "
                      "terminated by user")
@click.option("--shell", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
def fullauto(shell, debug):
    """Creates and connects to bastion sessions
     automatically until terminated"""
    setup_debug(debug)

    while True:
        Bastion.create_managed_loop(shell=shell)

        Bastion.connected = False
        Bastion.active_tunnel = None
        Bastion.response = None

        sleep(1)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, Bastion.kill_bastion)
    signal.signal(signal.SIGTERM, Bastion.kill_bastion)
    cli()
