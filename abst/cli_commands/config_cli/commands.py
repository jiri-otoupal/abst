import click
import rich
from InquirerPy import inquirer

from abst.bastion_support.oci_bastion import Bastion
from abst.cfg_func import __upgrade
from abst.config import default_contexts_location
from abst.utils.misc_funcs import setup_calls
from abst.tools import get_context_path


@click.group(help="Group of commands for operations with config")
def config():
    pass


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
