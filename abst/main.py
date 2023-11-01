import os
import signal

import click
import rich
from InquirerPy import inquirer

from abst.__version__ import __version_name__, __version__
from abst.bastion_support.bastion_scheduler import BastionScheduler
from abst.bastion_support.oci_bastion import Bastion
from abst.cli_commands.config_cli.commands import config
from abst.cli_commands.context.commands import context
from abst.cli_commands.cp_cli.commands import cp
from abst.cli_commands.create_cli.commands import create
from abst.cli_commands.helm_cli.commands import helm
from abst.cli_commands.kubectl_cli.commands import ssh_pod, log_pod
from abst.cli_commands.parallel.commands import parallel
from abst.config import default_creds_path, default_contexts_location, default_conf_path
from abst.utils.misc_funcs import setup_calls


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

    Bastion.create_default_location()
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
    Bastion.create_default_location()
    cli()


signal.signal(signal.SIGINT, BastionScheduler.kill_all)
signal.signal(signal.SIGTERM, BastionScheduler.kill_all)
signal.signal(signal.SIGABRT, BastionScheduler.kill_all)

cli.add_command(parallel)
cli.add_command(config)
cli.add_command(context)
cli.add_command(helm)
cli.add_command(cp)
cli.add_command(ssh_pod)
cli.add_command(log_pod)
cli.add_command(create)

if __name__ == "__main__":
    main()
