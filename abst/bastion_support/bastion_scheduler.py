import signal
from threading import Thread
from time import sleep

import rich
from click import clear
from rich.align import Align

from abst.config import default_stack_location, default_stack_contents, \
    default_contexts_location
from abst.bastion_support.oci_bastion import Bastion
from abst.wrappers import load_stack_decorator


class BastionScheduler:
    __dry_stack = set()
    __live_stack = set()
    stopped = False

    @classmethod
    def load_stack(cls):
        if not default_stack_location.exists():
            Bastion.write_creds_json(default_stack_contents, default_stack_location)
        if default_stack_location.exists():
            cls.__dry_stack = set(Bastion.load_json(default_stack_location)["stack"])

    @classmethod
    def update_stack(cls):
        if default_stack_location.exists():
            Bastion.write_creds_json({"stack": list(cls.__dry_stack)},
                                     default_stack_location)

    @classmethod
    def get_contexts(cls):
        return [name.name.replace(".json", "") for name in
                default_contexts_location.iterdir()]

    @classmethod
    @load_stack_decorator
    def add_bastion(cls, context_name: str):
        if context_name in cls.__dry_stack:
            print("Already in stack")
            return

        if context_name != "default" and context_name not in cls.get_contexts():
            print(f"No context with name {context_name}")
            return

        if (res := cls.local_port_in_stack(context_name))[0]:
            rich.print(
                f"[red]Local port is already taken by {res[1].context_name}[/red]")
            return

        cls.__dry_stack.add(context_name)
        rich.print(f"[green]Added Bastion {context_name}[/green]")
        cls.update_stack()

    @classmethod
    @load_stack_decorator
    def remove_bastion(cls, name: str):
        try:
            cls.__dry_stack.remove(name)
            rich.print(f"[green]Removed Bastion {name}[/green]")
            cls.update_stack()
        except KeyError:
            rich.print(f"[red]No Bastion by name {name} in stack[/red]")

    @classmethod
    def __display(cls, console):
        console.clear()
        from rich.table import Table
        table = Table(title="Bastion Sessions", highlight=True)
        table.add_column("Name", justify="left", style="cyan", no_wrap=True)
        table.add_column("Local Port", style="magenta", no_wrap=True)
        table.add_column("Active", justify="right", style="green", no_wrap=True)
        table.add_column("Status", justify="right", style="green", no_wrap=True)
        for bastion in cls.__live_stack:
            conf = bastion.load_self_creds()
            active = bastion.connected and bastion.active_tunnel.poll() is None
            name = "default" if bastion.context_name is None else bastion.context_name

            try:
                table.add_row(name, conf.get('local-port', 'Not Specified'), str(active),
                              bastion.current_status)
            except:
                pass
        centered_table = Align.center(table)
        console.print(centered_table)

    @classmethod
    def __display_loop(cls):
        from rich.console import Console
        console = Console()
        signal.signal(signal.SIGINT, BastionScheduler.kill_all)
        signal.signal(signal.SIGTERM, BastionScheduler.kill_all)
        while True:
            clear()
            cls.__display(console)
            sleep(3)

    @classmethod
    def _run_indefinitely(cls, func):
        while True:
            if cls.stopped:
                return
            try:
                func()
            finally:
                sleep(1)

    @classmethod
    @load_stack_decorator
    def run(cls):
        signal.signal(signal.SIGINT, BastionScheduler.kill_all)
        signal.signal(signal.SIGTERM, BastionScheduler.kill_all)
        rich.print("Will run all Bastions in parallel")
        thread_list = []

        for context_name in cls.__dry_stack:
            if cls.stopped:
                return
            bastion = Bastion(None if context_name == "default" else context_name)
            cls.__live_stack.add(bastion)
            t = Thread(name=context_name, target=cls._run_indefinitely,
                       args=[bastion.create_forward_loop], daemon=True)
            thread_list.append(t)
            t.start()
            rich.print(f"Started {context_name}")

        cls.__display_loop()

    @classmethod
    @load_stack_decorator
    def local_port_in_stack(cls, context_name: str):
        path = Bastion.get_creds_path_resolve(context_name)
        instance_creds = Bastion.load_json(path)
        for context_name in cls.__dry_stack:
            b_creds = Bastion.load_json(Bastion.get_creds_path_resolve(context_name))
            if b_creds["local-port"] == instance_creds["local-port"]:
                return True, context_name
        return False, None

    @classmethod
    def kill_all(cls, a=None, b=None, c=None):
        # This should be only executed in running state
        cls.stopped = True
        blist_copy = list(Bastion.session_list)
        for i, sess in enumerate(blist_copy):
            try:
                print(f"Killing {sess}")
                Bastion.current_status = "deleting"
                Bastion.delete_bastion_session(sess)
            except Exception:
                print(f"Looks like Bastion is already deleted {sess}")
            finally:
                print(f"Deleting {i + 1}/{len(blist_copy)}")
        exit(0)

    @classmethod
    @load_stack_decorator
    def get_bastions(cls) -> tuple:
        return tuple(cls.__dry_stack)
