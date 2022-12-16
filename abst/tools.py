from abst.bastion_support.bastion_scheduler import BastionScheduler
from abst.config import default_creds_path, default_contexts_location
from abst.bastion_support.oci_bastion import Bastion


def get_context_path(context_name):
    if context_name is None:
        return default_creds_path
    else:
        return default_contexts_location / (context_name + ".json")


def display_scheduled():
    from rich.table import Table
    from rich.console import Console
    console = Console()
    table = Table(title="Current Bastions in Stack", highlight=True)

    table.add_column("Name", justify="left", style="cyan", no_wrap=True)
    table.add_column("Local Port", style="magenta", no_wrap=True)
    table.add_column("Active", justify="right", style="green", no_wrap=True)
    table.add_column("Status", justify="right", style="green", no_wrap=True)

    for context_name in BastionScheduler.get_bastions():
        conf = Bastion.load_json(Bastion.get_creds_path_resolve(context_name))
        table.add_row(context_name, conf.get('local-port', 'Not Specified'),
                      conf.get('target-ip', 'Not Specified'),
                      conf.get('target-port', 'Not Specified'))
    console.print(table)
