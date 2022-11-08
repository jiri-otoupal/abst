import rich

from abst.bastion_scheduler import BastionScheduler
from abst.config import default_creds_path, default_contexts_location
from abst.oci_bastion import Bastion


def get_context_path(context_name):
    if context_name is None:
        return default_creds_path
    else:
        return default_contexts_location / (context_name + ".json")


def display_scheduled():
    rich.print("Current Bastions in Stack:")
    for context_name in BastionScheduler.get_bastions():
        conf = Bastion.load_json(Bastion.get_creds_path_resolve(context_name))
        rich.print(
            f"Bastion: [green]{context_name}[/green] "
            f"Local Port: [red]{conf.get('local-port', 'Not Specified')}[/red] "
            f"Target: [orange]{conf.get('target-ip', 'Not Specified')}"
            f":{conf.get('target-port', 'Not Specified')}[/orange]")
