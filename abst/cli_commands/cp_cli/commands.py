import os

import click
import rich

from abst.utils.misc_funcs import setup_calls


@click.group("cp", help="Copy commands for special usage")
def cp():
    pass


@cp.command("login", help="Login to docker and helm registry")
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
