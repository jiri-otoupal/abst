import click
import rich
from InquirerPy import inquirer

from abst.cli_commands.ssh_cli.utils import filter_keys_by_substring, filter_keys_by_port, do_ssh
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
    data = lb.list_contents()

    if len(data.keys()) == 0:
        rich.print("[yellow]No connected sessions[/yellow]")

    if name and len(keys := filter_keys_by_substring(data, name)) == 1:
        do_ssh(keys[0], data[keys[0]]["username"], data[keys[0]]["port"])
        return

    if port is not None and len(keys := filter_keys_by_port(data, port)) == 1:
        do_ssh(keys[0], data[keys[0]]["username"], data[keys[0]]["port"])
        return

    if (key_lens := [len(key) for key in data.keys()]) and len(key_lens) > 0:
        longest_key = max(key_lens)
    else:
        rich.print(f"[yellow]No alive contexts found[/yellow]")
        return

    for key, value in data.items():
        value["compatible"] = len({"username", "port"} - set(value.keys())) == 0

    questions = [
        {"name": f"{key.ljust(longest_key)} |= status: {data['status']} | Context compatible: {data['compatible']}",
         "value": (key, data)} for
        key, data
        in data.items()]

    context_name, context = inquirer.select("Select context to ssh to:", questions).execute()

    if "username" not in context:
        rich.print("[red]Please fill resource-os-username into config for this feature to work[/red]")
        return
    elif "port" not in context:
        rich.print("[red]Please fill local-port into config for this feature to work[/red]")
        return

    do_ssh(context_name, context["username"], context["port"])
