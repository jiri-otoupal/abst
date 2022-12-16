import rich
from InquirerPy import inquirer

from abst.config import default_config_keys
from abst.bastion_support.oci_bastion import Bastion


def __upgrade(context_name, path):
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
