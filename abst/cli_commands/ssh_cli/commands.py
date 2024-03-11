import click

from abst.utils.misc_funcs import setup_calls


@click.command("ssh", help="Will SSH into pod with containing string name")
@click.argument("port", required=False, default=None)
@click.option("-n", "--name", default=None, help="Name of context running, it can be just part of the name")
@click.option("--debug", is_flag=True, default=False)
def ssh_pod(port, name, debug):
    setup_calls(debug)
