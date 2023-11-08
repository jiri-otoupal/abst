from pathlib import Path
from typing import Optional

from abst.bastion_support.bastion_scheduler import BastionScheduler
from abst.bastion_support.oci_bastion import Bastion
from abst.config import default_creds_path, default_contexts_location


def get_context_path(context_name):
    if context_name is None:
        return default_creds_path
    else:
        return default_contexts_location / (context_name + ".json")


def display_scheduled(set_dir: Optional[Path] = None):
    from rich.table import Table
    from rich.console import Console
    console = Console()
    table = Table(title=f"Bastions of {set_dir.name} set" if set_dir else "Bastions of default stack", highlight=True)

    table.add_column("Name", justify="left", style="cyan", no_wrap=True)
    table.add_column("Local Port", style="magenta", no_wrap=True)
    table.add_column("Active", justify="right", style="green", no_wrap=True)
    table.add_column("Status", justify="right", style="green", no_wrap=True)
    if set_dir:
        for context_path in filter(lambda p: not str(p.name).startswith("."), set_dir.iterdir()):
            conf = Bastion.load_json(context_path)
            context_name = context_path.name[:-5]
            table.add_row(context_name, conf.get('local-port', 'Not Specified'),
                          conf.get('target-ip', 'Not Specified'),
                          conf.get('target-port', 'Not Specified'))
    else:
        for context_path in BastionScheduler.get_bastions():
            conf = Bastion.load_json(Bastion.get_creds_path_resolve(context_path))
            table.add_row(context_path, conf.get('local-port', 'Not Specified'),
                          conf.get('target-ip', 'Not Specified'),
                          conf.get('target-port', 'Not Specified'))
    console.print(table)
