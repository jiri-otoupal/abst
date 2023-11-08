import json
from json import JSONDecodeError
from pathlib import Path

import rich
from InquirerPy import inquirer

from abst.bastion_support.oci_bastion import Bastion
from abst.config import default_config_keys, default_contexts_location, default_parallel_sets_location


def __upgrade(context_name, path, _all):
    if not _all:
        creds_json_ro = Bastion.load_json(Bastion.get_creds_path_resolve(context_name))
        missing_keys = set(default_config_keys).difference(creds_json_ro.keys())
        res_json = dict(creds_json_ro)
        for key in missing_keys:
            res_json[key] = "!!! New Key !!! <- This was upgraded"
        rich.print_json(data=res_json)
        if inquirer.confirm(message="Write New Json ?", default=False).execute():
            Bastion.write_creds_json(res_json, path)
            rich.print("[green]Wrote changes[/green]")
        else:
            rich.print("[red]Fill interrupted, nothing changed[/red]")

    rich.print("Searching contexts for upgrade to minimized version...")

    minimize_files = []

    for file in default_contexts_location.iterdir():
        append_minimizable(file, minimize_files)
    for set_folder in filter(lambda p: not str(p.name).startswith("."), default_parallel_sets_location.iterdir()):
        for file in set_folder.iterdir():
            if file.name.startswith(".") or not append_minimizable(file, minimize_files):
                continue
    if not len(minimize_files):
        rich.print("No minimizable files found")
        return
    if inquirer.confirm("Do you want to minimize those contexts?").execute():
        for file, data in minimize_files:
            with open(file, "w") as f:
                data.pop("ssh-pub-path", "")
                data.pop("private-key-path", "")
                rich.print(f"Minimizing {f.name}...")
                json.dump(data, f, indent=4)


def append_minimizable(file, minimize_files) -> bool:
    conf = Bastion.load_config()
    with open(file, "r") as f:
        try:
            data = json.load(f)
            if type(data) is not dict:
                return False
        except (JSONDecodeError, UnicodeDecodeError):
            return False
        if Path(data.get("ssh-pub-path", "")).name == Path(conf.get("ssh-pub-path")).name or \
                Path(data.get("private-key-path", "")).name == Path(conf.get("private-key-path")).name:
            rich.print(f" > Minimizable context {file}")
            minimize_files.append((file, data))
            return True
