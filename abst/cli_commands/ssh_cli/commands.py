import os

import click
import rich
from InquirerPy import inquirer

from abst.config import broadcast_shm_name
from abst.sharing.local_broadcast import LocalBroadcast
from abst.utils.misc_funcs import setup_calls


@click.command("ssh", help="Will SSH into pod with containing string name")
@click.argument("port", required=False, default=None)
@click.option("-n", "--name", default=None, help="Name of context running, it can be just part of the name")
@click.option("--debug", is_flag=True, default=False)
def ssh_lin(port, name, debug):
    setup_calls(debug)

    lb = LocalBroadcast(broadcast_shm_name)
    data = lb.retrieve_json()
    longest_key = max(len(key) for key in data.keys())
    questions = [{"name": f"{key.ljust(longest_key)} |= status: {data['status']}", "value": (key, data)} for key, data
                 in data.items()]

    context_name, context = inquirer.select("Select context to ssh to:", questions).execute()
    rich.print(f"[green]Running SSH to {context_name}[/green] "
               f"[yellow]{context['username']}@localhost:{context['port']}[/yellow]")
    os.system(f'ssh {context["username"]}@127.0.0.1 -p {context["port"]}')
