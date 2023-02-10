import logging
import os
import re
import signal
import subprocess
from time import sleep

import click
import rich
from InquirerPy import inquirer
from rich.logging import RichHandler

from abst.__version__ import __version_name__, __version__
from abst.bastion_support.bastion_scheduler import BastionScheduler
from abst.cfg_func import __upgrade
from abst.config import default_creds_path, default_contexts_location, default_conf_path
from abst.dialogs import helm_login_dialog
from abst.notifier.version_notifier import Notifier
from abst.bastion_support.oci_bastion import Bastion
from abst.tools import get_context_path, display_scheduled


@click.group()
@click.version_option(f"{__version__} {__version_name__}")
def cli():
    pass


@cli.group(help="Group of commands for operations with config")
def config():
    pass


@cli.group(help="Parallel Bastion Control group")
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
def run(debug):
    setup_calls(debug)
    display_scheduled()
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
    BastionScheduler.run()


@parallel.command("display", help="Display current Bastions is stack")
@click.option("--debug", is_flag=True, default=False)
def display(debug):
    setup_calls(debug)

    display_scheduled()


@cli.command(
    "use",
    help="Will Switch context to be used,"
    " use default for default context specified"
    " in creds.json",
)
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default="")
def use(debug, context_name):
    setup_calls(debug)

    used_context = context_name
    if context_name == "":
        contexts = BastionScheduler.get_contexts()
        if len(contexts) == 0:
            rich.print("No Contexts available, selected default")
            used_context = "default"
        else:
            contexts.insert(0, "default")
            used_context = inquirer.select("Select context to use:", contexts).execute()

    Bastion.create_default_location()
    conf = Bastion.load_config()
    conf["used_context"] = None if used_context == "default" else used_context

    rich.print("[green]Successfully Switched[/green]")
    rich.print(
        f"[white]Currently used context is[/white] [green]{used_context}[/green] "
        f"[gray](This does not change context in .kube)[/gray]"
    )
    Bastion.write_creds_json(conf, default_conf_path)


@config.command("generate", help="Will generate sample json and overwrite changes")
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def generate(debug, context_name):
    setup_calls(debug)

    path = get_context_path(context_name)

    Bastion.create_default_location()
    td = Bastion.generate_sample_dict()
    creds_path = Bastion.write_creds_json(td, path)
    print(
        f"Sample credentials generated, please fill 'creds.json' in {creds_path} with "
        f"your credentials for this to work, you can use 'abst json fill "
        f"{context_name if context_name else ''}'"
    )


@config.command(
    "fill", help="Fills Json config with credentials you enter interactively"
)
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def fill(debug, context_name):
    setup_calls(debug)

    path = get_context_path(context_name)

    if not path.exists():
        rich.print("Generating sample Creds file")
        Bastion.create_default_location()
        td = Bastion.generate_sample_dict()
        Bastion.write_creds_json(td, path)

    if not default_contexts_location.exists():
        rich.print("Generating contexts location")
        Bastion.create_default_location()

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


@config.command(
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


@config.command(
    "upgrade", help="Locates Json config with credentials you enter interactively"
)
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def upgrade(debug, context_name):
    setup_calls(debug)

    path = get_context_path(context_name)

    if not path.exists():
        rich.print("[green]No config to upgrade[/green]")
        return

    __upgrade(context_name, path)


@cli.command("clean", help="Cleans all credentials created by abst")
def clean():
    """ """

    files = [*default_contexts_location.iterdir()]
    if default_creds_path.exists():
        files.append(default_creds_path)
    try:
        confirm = inquirer.confirm(
            "Do you really want to Delete all Creds file ? All of credentials will be "
            "lost"
        ).execute()
        if not confirm:
            rich.print("[green]Cancelling, nothing changed[/green]")
            exit(0)

        rich.print("[red]Deleting all of the credentials[/red]")
        for file in files:
            os.remove(str(file))
    except PermissionError:
        print("Do not have permission to remove, or process is using this file.")
        print(f"Please delete manually in {file}")


@cli.group(help="Group of commands for creating Bastion sessions")
def create():
    signal.signal(signal.SIGINT, BastionScheduler.kill_all)
    signal.signal(signal.SIGTERM, BastionScheduler.kill_all)


def setup_calls(debug):
    setup_debug(debug)
    Notifier.notify()


def setup_debug(debug):
    if not debug:
        logging.disable(logging.DEBUG)
        logging.disable(logging.INFO)

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.CRITICAL,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )


@create.group(help="Group of commands for Creating Port Forward Sessions")
def forward():
    pass


@create.group(help="Group of commands for Creating Managed SSH Sessions")
def managed():
    pass


@forward.command(
    "single",
    help="Creates only one bastion session and keeps reconnecting until"
    " its deleted, does not create any more Bastion sessions",
)
@click.option("--shell", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def single_forward(shell, debug, context_name):
    """Creates only one bastion session
    ,connects and reconnects until its ttl runs out"""
    setup_calls(debug)

    if context_name is None:
        conf = Bastion.load_config()
        used_name = conf["used_context"]
    else:
        used_name = context_name

    Bastion(used_name).create_forward_loop(shell=shell)


@forward.command(
    "fullauto",
    help="Creates and connects to Bastion session indefinitely until "
    "terminated by user",
)
@click.option("--shell", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def fullauto_forward(shell, debug, context_name):
    """Creates and connects to bastion sessions
    automatically until terminated"""

    setup_calls(debug)
    if context_name is None:
        conf = Bastion.load_config()
        used_name = conf["used_context"]
    else:
        used_name = context_name

    while True:
        Bastion(used_name).create_forward_loop(shell=shell)

        sleep(1)


@managed.command(
    "single",
    help="Creates only one bastion session and keeps reconnecting until"
    " its deleted, does not create any more Bastion sessions",
)
@click.option("--shell", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def single_managed(shell, debug, context_name):
    """Creates only one bastion session
    ,connects and reconnects until its ttl runs out"""
    setup_calls(debug)
    if context_name is None:
        conf = Bastion.load_config()
        used_name = conf["used_context"]
    else:
        used_name = context_name

    Bastion(used_name).create_managed_loop(shell=shell)


@managed.command(
    "fullauto",
    help="Creates and connects to Bastion session indefinitely until "
    "terminated by user",
)
@click.option("--shell", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False)
@click.argument("context-name", default=None, required=False)
def fullauto_managed(shell, debug, context_name):
    """Creates and connects to bastion sessions
    automatically until terminated"""
    setup_calls(debug)

    if context_name is None:
        conf = Bastion.load_config()
        used_name = conf["used_context"]
    else:
        used_name = context_name

    while True:
        Bastion(used_name).create_managed_loop(shell=shell)

        sleep(1)


@cli.command("ssh", help="Will SSH into pod with containing string name")
@click.argument("pod_name")
@click.option("--debug", is_flag=True, default=False)
def ssh_pod(pod_name, debug):
    setup_calls(debug)
    found = list()
    try:
        rich.print("Fetching pods")
        pod_lines = (
            subprocess.check_output(f"kubectl get pods -A".split(" "))
            .decode()
            .split("\n")
        )
    except FileNotFoundError:
        rich.print("[red]kubectl not found on this machine[/red]")
        return

    for pod_line in pod_lines:
        if pod_name in pod_line:
            found.append(pod_line)

    if len(found) > 1:
        data = re.sub(
            " +",
            " ",
            inquirer.select("Found more pods, choose one:", list(found)).execute(),
        ).split(" ")
        pod_name_precise = data[1]
    elif len(found) == 1:
        tmp = found.pop()
        data = re.sub(" +", " ", tmp).split(" ")
        pod_name_precise = data[1]
    else:
        rich.print(f"[red]No pods with name {pod_name} found[/red]")
        return

    rich.print(
        f"[green]Connecting to {pod_name_precise} in namespace: {data[0]}[/green]"
    )
    os.system(
        f"kubectl exec -n {data[0]} --stdin --tty {pod_name_precise} -- /bin/bash"
    )


@cli.group("cp")
def cp():
    pass


@cli.group("helm")
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


@cp.command("login")
@click.argument("secret_name")
@click.argument("source_namespace")
@click.argument("target_namespace")
@click.option("--debug", is_flag=True, default=False)
def cp_secret(
    secret_name: str,
    target_namespace: str,
    source_namespace: str = "default",
    debug=False,
):
    """
    Copy Secret in current cluster from source namespace to target
    @param secret_name: Secret Name
    @param target_namespace: Target Namespace name
    @param source_namespace: Source Namespace name
    @return:
    :param debug:
    """
    setup_calls(debug)
    try:
        rich.print("Trying Copy secret")
        os.system(
            f"kubectl get secret {secret_name} --namespace={source_namespace} -o yaml | sed "
            f"'s/namespace: .*/namespace: {target_namespace}/' | kubectl apply -f -"
        )
    except FileNotFoundError:
        rich.print("[red]kubectl not found on this machine[/red]")
        return


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )
    Bastion.create_default_location()
    cli()


signal.signal(signal.SIGINT, BastionScheduler.kill_all)
signal.signal(signal.SIGTERM, BastionScheduler.kill_all)
signal.signal(signal.SIGABRT, BastionScheduler.kill_all)

if __name__ == "__main__":
    main()
