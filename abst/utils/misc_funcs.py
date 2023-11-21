import json
import logging
import os
import subprocess
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Optional

import rich
from rich.logging import RichHandler

from abst.bastion_support.oci_bastion import Bastion
from abst.config import default_contexts_location


def setup_calls(debug):
    setup_debug(debug)


def setup_debug(debug):
    if not debug:
        logging.disable(logging.DEBUG)
        logging.disable(logging.INFO)
    from imp import reload  # python 2.x don't need to import reload, use it directly
    reload(logging)
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.CRITICAL,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )


def print_eligible(searched: str):
    contexts = Bastion.get_contexts()
    rich.print("[bold]Configured contexts:[/bold]")
    for key, context in contexts.items():
        do_skip = False
        for value in context.values():
            if searched in value:
                do_skip = True
                break
        if do_skip:
            continue
        rich.print(key)


def get_context_data(name) -> Optional[dict]:
    if name in [file.name.replace(".json", "") for file in
                Path(default_contexts_location).iterdir()]:
        rich.print("[bold]Context config contents:[/bold]\n")
        with open(Path(default_contexts_location) / (name + ".json"), "r") as f:
            data = json.load(f)
            return data
    else:
        rich.print("[red]Context does not exists[/red]")
        return None


def fetch_pods():
    rich.print("Fetching pods")
    pod_lines = (
        subprocess.check_output(f"kubectl get pods -A".split(" "))
        .decode()
        .split("\n")
    )
    return pod_lines


def recursive_copy(dir_to_iter: Path, dest_path: str, exclude: str, data: list, pod_name_precise: str,
                   thread_list: list):
    if dir_to_iter.is_dir():
        create_folder_kubectl(data, dest_path, pod_name_precise)

    for file in dir_to_iter.iterdir():
        final_dest_path = make_final_dest_path(dest_path, file)
        if file.name == exclude:
            rich.print(f"   [yellow]{file} excluded.[/yellow]")
            continue
        elif file.is_dir():
            rich.print(f"[yellow]Recursion to folder {file}[/yellow]")

            create_folder_kubectl(data, final_dest_path, pod_name_precise)
            t = Thread(name=f"recursive_copy_{file}", target=recursive_copy,
                       args=[file, dest_path, exclude, data, pod_name_precise, thread_list])
            t.start()
            thread_list.append(t)
        else:
            copy_file_alt_kubectl(data, final_dest_path, file, pod_name_precise)


def make_final_dest_path(dest_path, file):
    sub_path = str(file).split("/")

    fsp = sub_path[sub_path.index(Path(dest_path).name) + 1:]

    final_dest_path = f"{dest_path}{'/' if len(fsp) > 0 else ''}{'/'.join(fsp)}"
    return final_dest_path


def create_folder_kubectl(data: list, dest_path: str, pod_name_precise: str):
    kubectl_create_dir_cmd = (f"kubectl"
                              f" exec -i {pod_name_precise} -n {data[0]} -- mkdir -p \"{dest_path}\"")
    logging.info(f"Executing {kubectl_create_dir_cmd}")
    os.system(kubectl_create_dir_cmd)


def copy_file_alt_kubectl(data: list, dest_path: str, local_path: Path, pod_name_precise: str, tries=4):
    kubectl_alt_copy_cmd = (f"cat \"{local_path}\" |"
                            f" kubectl exec -i {pod_name_precise} -n {data[0]} -- tee \"{dest_path}\" > /dev/null")
    logging.info(f"Executing {kubectl_alt_copy_cmd}")
    exit_code = subprocess.call(kubectl_alt_copy_cmd, shell=True)
    rich.print(
        f"   [green]{local_path if type(local_path) == str else local_path.name}"
        f" ({'?' if type(local_path) == str else local_path.stat().st_size / 1000} kB)"
        f" successfully copied![/green]")
    if exit_code != 0 and tries < 0:
        rich.print("[red]Failed to copy.[/red]")
        exit(1)
    elif exit_code != 0 and tries > 0:
        rich.print(f"Failed to copy will try again, try {tries}/4")
        sleep(5)
        copy_file_alt_kubectl(data, dest_path, local_path, pod_name_precise, tries - 1)
