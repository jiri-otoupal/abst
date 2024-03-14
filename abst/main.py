import os
import sys
import threading

import click
import rich
import semantic_version
from InquirerPy import inquirer
from requests import ConnectTimeout

from abst.__version__ import __version_name__, __version__, __change_log__
from abst.bastion_support.bastion_scheduler import BastionScheduler
from abst.bastion_support.oci_bastion import Bastion
from abst.cli_commands.context.commands import context, ctx
from abst.cli_commands.cp_cli.commands import cp
from abst.cli_commands.create_cli.commands import create, _do
from abst.cli_commands.helm_cli.commands import helm
from abst.cli_commands.kubectl_cli.commands import pod
from abst.cli_commands.parallel.commands import parallel, pl
from abst.cli_commands.ssh_cli.commands import ssh_lin
from abst.config import default_creds_path, default_contexts_location, default_conf_path
from abst.notifier.version_notifier import Notifier
from abst.utils.misc_funcs import setup_calls, link_signals


@click.group()
@click.version_option(f"{__version__} {__version_name__}")
def cli():
    pass


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

    Bastion.create_default_locations()
    conf = Bastion.load_config()
    conf["used_context"] = None if used_context == "default" else used_context

    rich.print("[green]Successfully Switched[/green]")
    rich.print(
        f"[white]Currently used context is[/white] [green]{used_context}[/green] "
        f"[gray](This does not change context in .kube)[/gray]"
    )
    Bastion.write_creds_json(conf, default_conf_path)


@cli.command("clean", help="Cleans all credentials created by abst")
def clean():
    """ """
    file = "not specified"
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


def main():
    sys.setrecursionlimit(2097152)
    threading.stack_size(134217728)

    _config = Bastion.load_config()
    current_version = semantic_version.Version(_config["changelog-version"])
    package_version = semantic_version.Version(__version__)
    if (_config.get("changelog-version", None) is None or current_version < package_version) and __change_log__:
        _config["changelog-version"] = __version__
        Bastion.write_creds_json(_config, default_conf_path)
        print_changelog(_config)

    try:
        Notifier.notify()
    except (ConnectionError, ConnectTimeout):
        return False
    Bastion.create_default_locations()
    cli()


def print_changelog(_config):
    rich.print(f"[yellow]Version {__version__} {__version_name__}[/yellow]")
    rich.print("[red]Changelog[/red]")
    rich.print(f"[yellow]{__change_log__}[/yellow]")


link_signals()

cli.add_command(parallel)
cli.add_command(pl)
cli.add_command(context)
cli.add_command(ctx)
cli.add_command(helm)
cli.add_command(cp)
cli.add_command(pod)
cli.add_command(create)
cli.add_command(_do)
cli.add_command(ssh_lin)

if __name__ == "__main__":
    main()
