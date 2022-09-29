import os
import signal
from time import sleep

import click
import rich
from InquirerPy import inquirer

from abst.config import default_creds_path
from abst.oci_bastion import Bastion


# Press the green button in the gutter to run the script.
def main():
    cli()


@click.group()
def cli():
    pass


@cli.group(help="Group of commands for operations with config")
def config():
    pass


@config.command("generate", help="Will generate sample json and overwrite changes")
def generate():
    td = Bastion.generate_sample_dict()
    creds_path = Bastion.write_creds_json(td)
    print(
        f"Sample credentials generated, please fill 'creds.json' in {creds_path} with "
        f"your credentials for this to work, you can use 'abst json fill'")


@config.command("fill", help="Fills Json config with credentials you enter interactively")
def fill():
    if not default_creds_path.exists():
        print("Generating sample Creds file")
        td = Bastion.generate_sample_dict()
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


@create.command("single",
                help="Creates only one bastion session and keeps reconnecting until"
                     " its deleted, does not create any more Bastion sessions")
@click.option("--shell", is_flag=True, default=False)
def single(shell):
    """Creates only one bastion session
     ,connects and reconnects until its ttl runs out"""
    Bastion.create_bastion(shell=shell)


@create.command("fullauto",
                help="Creates and connects to Bastion session indefinitely until "
                     "terminated by user")
@click.option("--shell", is_flag=True, default=False)
def fullauto(shell):
    """Creates and connects to bastion sessions
     automatically until terminated"""

    while True:
        print("Creating New Bastion Session")
        Bastion.create_bastion(shell=shell)

        Bastion.connected = False
        Bastion.active_tunnel = None
        Bastion.response = None

        sleep(1)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, Bastion.kill_bastion)
    signal.signal(signal.SIGTERM, Bastion.kill_bastion)
    cli()
