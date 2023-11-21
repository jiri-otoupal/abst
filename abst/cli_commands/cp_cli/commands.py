import logging
import os
import re
from pathlib import Path
from subprocess import call

import click
import rich
from InquirerPy import inquirer

from abst.utils.misc_funcs import setup_calls, fetch_pods, recursive_copy, copy_file_alt_kubectl


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
        kubectl_copy_secret_cmd = f"kubectl get secret {secret_name} --namespace={source_namespace} -o yaml | sed " \
                                  f"'s/namespace: .*/namespace: {target_namespace}/' | kubectl apply -f -"
        logging.info(f"Executing {kubectl_copy_secret_cmd}")

        os.system(
            kubectl_copy_secret_cmd
        )
    except FileNotFoundError:
        rich.print("[red]kubectl not found on this machine[/red]")
        return


@cp.command("file", help="Will copy file into pod with containing string name")
@click.argument("pod_name", type=str)
@click.argument("local_path", type=str)
@click.argument("dest_path", type=str)
@click.option("--exclude", default="", type=str)
@click.option("--debug", is_flag=True, default=False)
def cp_to_pod(pod_name, local_path, dest_path, exclude, debug):
    setup_calls(debug)

    try:
        pod_lines = fetch_pods()
    except FileNotFoundError:
        rich.print("[red]kubectl not found on this machine[/red]")
        return

    found = list(filter(lambda pod_line: pod_name in pod_line, pod_lines))

    if len(found) > 1:
        data = re.sub(
            " +",
            " ",
            inquirer.select("Found more pods, choose one:", list(found)).execute(),
        ).split(" ")
        pod_name_precise = data[1]
    elif len(found) == 1:
        tmp = found.pop()
        data = re.sub(" +", " ", tmp).split(" ")
        pod_name_precise = data[1]
    else:
        rich.print(f"[red]No pods with name {pod_name} found[/red]")
        return

    rich.print(
        f"[green]Copying file {local_path} to {pod_name_precise}:{dest_path} in namespace: {data[0]}[/green]"
    )
    kubectl_copy_cmd = f"kubectl cp {local_path} {data[0]}/{pod_name_precise}:{dest_path}"
    logging.info(f"Executing {kubectl_copy_cmd}")

    exit_code = call(
        kubectl_copy_cmd.split(" ")
    )

    if exit_code == 255:
        rich.print("[red]Failed to copy using conventional kubectl cp, probably missing [yellow]tar[/yellow] "
                   "executable[/red]")
        rich.print("[yellow]Trying alternative copy method...[/yellow]")
    else:
        return
    local_path_obj = Path(local_path).expanduser().resolve()
    thread_list = []

    if not local_path_obj.is_dir():
        copy_file_alt_kubectl(data, dest_path, local_path, pod_name_precise)
        return

    recursive_copy(local_path_obj, dest_path, exclude, data, pod_name_precise, thread_list)

    for t in thread_list:
        t.join()
