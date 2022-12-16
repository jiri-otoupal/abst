import lastversion
import rich
import semantic_version

from abst import __version__


class Notifier:
    @classmethod
    def get_last_version(cls):
        return lastversion.latest(__version__.__pypi_repo__)

    @classmethod
    def is_last_version(cls):
        last = cls.get_last_version()
        return semantic_version.Version(__version__.__version__) >= semantic_version.Version(str(last))

    @classmethod
    def notify(cls):
        if not cls.is_last_version():
            last = cls.get_last_version()
            rich.print(
                f"[yellow]WARNING: You are using abst version {__version__.__version__}; however,"
                f" version {last} is available.[/yellow]")
            rich.print(
                f"[yellow]You should consider upgrading via the `[green]pip3 install abst --upgrade[/green]`"
                f" command.[/yellow]")
