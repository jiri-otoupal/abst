from datetime import datetime

import eventlet
import lastversion
import requests
import rich
import semantic_version
from requests import ConnectTimeout

from abst import __version__
from abst.config import default_conf_path


class Notifier:
    @classmethod
    def check_pypi_available(cls):
        try:
            req = requests.get("https://pypi.org/", timeout=0.2)
            return req.status_code == 200
        except (ConnectionError, ConnectTimeout):
            return False

    @classmethod
    def get_last_version(cls):
        return lastversion.latest(__version__.__pypi_repo__)

    @classmethod
    def is_last_version(cls):
        last = cls.get_last_version()
        return semantic_version.Version(
            __version__.__version__) >= semantic_version.Version(str(last))

    @classmethod
    def notify(cls):
        from abst.bastion_support.oci_bastion import Bastion
        cfg = Bastion.load_config()
        dt = datetime.now()
        if (dt - datetime.fromtimestamp(
                cfg.get("last-check", 1677884000))).seconds < 60 * 60 * 8:
            return

        cfg["last-check"] = datetime.timestamp(dt)
        Bastion.write_creds_json(cfg, default_conf_path)

        if cls.check_pypi_available() and not cls.is_last_version():
            last = cls.get_last_version()
            rich.print(
                f"[yellow]WARNING: You are using abst version {__version__.__version__}; however,"
                f" version {last} is available.[/yellow]")
            rich.print(
                f"[yellow]You should consider upgrading via the `[green]pip3 install abst --upgrade[/green]`"
                f" command.[/yellow]")
