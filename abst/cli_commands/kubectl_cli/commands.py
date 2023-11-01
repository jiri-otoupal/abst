import os
import re
import subprocess

import click
import rich
from InquirerPy import inquirer

from abst.utils.misc_funcs import setup_calls


@click.command("ssh", help="Will SSH into pod with containing string name")
@click.argument("pod_name")
@click.option("--debug", is_flag=True, default=False)
def ssh_pod(pod_name, debug):
    setup_calls(debug)

    try:
        rich.print("Fetching pods")
        pod_lines = (
            subprocess.check_output(f"kubectl get pods -A".split(" "))
            .decode()
            .split("\n")
        )
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
        f"[green]Connecting to {pod_name_precise} in namespace: {data[0]}[/green]"
    )
    os.system(
        f"kubectl exec -n {data[0]} --stdin --tty {pod_name_precise} -- /bin/bash"
    )


@click.command("logs", help="Will get logs from a pod with containing string name")
@click.argument("pod_name")
@click.option("--debug", is_flag=True, default=False)
def log_pod(pod_name, debug):
    setup_calls(debug)

    try:
        rich.print("Fetching pods")
        pod_lines = (
            subprocess.check_output(f"kubectl get pods -A".split(" "))
            .decode()
            .split("\n")
        )
    except FileNotFoundError:
        rich.print("[red]kubectl not found on this machine[/red]")
        return

    found = list(filter(lambda pod_line: pod_name in pod_line, pod_lines))

    if len(found) > 1:
        data = re.sub(
            " +",
            " ",
            inquirer.select("Found more pods, choose one:", found).execute(),
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
        f"[green]Getting logs from {pod_name_precise} in namespace: {data[0]}[/green]"
    )
    os.system(
        f"kubectl -n {data[0]} logs {pod_name_precise}"
    )
