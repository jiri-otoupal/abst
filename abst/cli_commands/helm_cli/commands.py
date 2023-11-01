import os
import subprocess

import click
import rich
from InquirerPy import inquirer

from abst.bastion_support.oci_bastion import Bastion
from abst.config import default_conf_path
from abst.dialogs import helm_login_dialog
from abst.utils.misc_funcs import setup_calls


@click.group("helm", help="Commands for helm and docker")
def helm():
    pass


@helm.command("login")
@click.option("--debug", is_flag=True, default=False)
@click.option(
    "--edit",
    default=False,
    help="Edit credentials with index as argument (starts from 1)",
)
def helm_login(debug, edit):
    """
    Copy Secret in current cluster from source namespace to target
    @return:
    :param debug:
    """
    setup_calls(debug)
    from subprocess import PIPE

    try:
        _config = Bastion.load_config()
        if "helm" not in _config.keys():
            _config["helm"] = []
            host, password, remote, username = helm_login_dialog()
            _config["helm"].append(
                {
                    "host": host,
                    "remote": remote,
                    "username": username,
                    "password": password,
                }
            )
            Bastion.write_creds_json(_config, default_conf_path)
            rich.print("Added Credentials")
        elif edit:
            if "helm" not in _config.keys():
                _config["helm"] = []

            host, password, remote, username = helm_login_dialog()
            _config["helm"][edit - 1] = {
                "host": host,
                "remote": remote,
                "username": username,
                "password": password,
            }
            rich.print_json(data=_config["helm"][edit - 1])
            if inquirer.confirm(message="Write New Json ?", default=False).execute():
                Bastion.write_creds_json(_config, default_conf_path)
                rich.print("Edited Credentials")

        choices = [
            {"name": f'{choice["remote"]} {choice["username"]}', "value": choice}
            for choice in _config["helm"]
        ]

        selected = inquirer.select("Select login", choices).execute()
        rich.print("Trying to login")
        p = subprocess.Popen(
            f'helm registry login {selected["host"]} -u {selected["username"]} --password-stdin'.split(
                " "
            ),
            stdout=PIPE,
            stdin=PIPE,
            stderr=PIPE,
        )
        rich.print(p.communicate(input=selected["password"].encode())[0].decode())

    except Exception as ex:
        rich.print(f"[red]Exception during execution {ex}[/red]")
        return


@helm.command("push")
@click.argument("chart")
@click.option("--debug", is_flag=True, default=False)
def helm_push(chart, debug):
    """
    Copy Secret in current cluster from source namespace to target
    @return:
    :param debug:
    :param chart:
    :param debug:
    """
    setup_calls(debug)
    try:
        _config = Bastion.load_config()
        if "helm" not in _config.keys():
            _config["helm"] = []
            rich.print(
                f"Please Fill in Repository details that"
                f" are going to be saved in {default_conf_path}"
                f" with command 'abst helm login'"
            )
        choices = [
            {"name": f'{choice["remote"]} {choice["username"]}', "value": choice}
            for choice in _config["helm"]
        ]

        selected = inquirer.select("Select remote", choices).execute()
        rich.print("Trying to push")
        os.system(f'helm push {chart} {selected["remote"]}')

    except Exception as ex:
        rich.print(f"[red]Exception during execution {ex}[/red]")
        return
