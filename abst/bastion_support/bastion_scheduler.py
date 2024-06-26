from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Optional

import rich
from click import clear
from rich import print
from rich.align import Align

from abst.bastion_support.oci_bastion import Bastion
from abst.config import default_stack_location, default_stack_contents, \
    default_contexts_location
from abst.utils.misc_funcs import link_signals
from abst.wrappers import load_stack_decorator


class BastionScheduler:
    __dry_stack = set()
    __live_stack = set()
    stopped = False
    session_list = []

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
        link_signals()
        while True:
            clear()
            cls.__display(console)
            sleep(1)

    @classmethod
    def _run_indefinitely(cls, func, force: bool = False):
        while True:
            if cls.stopped:
                return
            try:
                func(force=force)
            finally:
                sleep(0.3)

    @classmethod
    @load_stack_decorator
    def run(cls, force=False, set_dir: Optional[Path] = None):
        link_signals()
        rich.print("Will run all Bastions in parallel")
        thread_list = []

        if not set_dir:
            for context_name in cls.__dry_stack:
                if cls.stopped:
                    return
                region = Bastion.load_json(Bastion.get_creds_path_resolve(context_name)).get("region", None)
                bastion = Bastion(None if context_name == "default" else context_name, region=region)
                Bastion.session_list.append(bastion)
                cls.session_list.append(bastion)
                cls.__live_stack.add(bastion)
                t = Thread(name=context_name, target=cls._run_indefinitely,
                           args=[bastion.create_forward_loop, force], daemon=True)
                thread_list.append(t)
                t.start()
                rich.print(f"Started {context_name}")
        else:
            for context_path in filter(lambda p: not str(p.name).startswith(".") and str(p.name).endswith(".json"),
                                       set_dir.iterdir()):
                if cls.stopped:
                    return
                context_name = context_path.name[:-5]
                region = Bastion.load_json(context_path).get("region", None)
                bastion = Bastion(None if context_name == "default" else context_name, region=region,
                                  direct_json_path=context_path)

                Bastion.session_list.append(bastion)
                cls.session_list.append(bastion)
                cls.__live_stack.add(bastion)
                t = Thread(name=context_name, target=cls._run_indefinitely,
                           args=[bastion.create_forward_loop, force], daemon=True)
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
    def kill_session(cls, sess, index, total):
        try:
            rich.print(f"[red]Killing[/red] {sess.bid}")
            Bastion.current_status = "deleting"
            sess.kill()
            Bastion.delete_bastion_session(sess.bid, sess.region)
        except Exception:
            pass

    @classmethod
    def kill_all(cls, a=None, b=None, c=None):
        # This should be only executed in running state
        cls.stopped = True
        blist_copy = list(cls.session_list)
        total_sessions = len(blist_copy)
        deleted = 0

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(cls.kill_session, sess, i + 1, total_sessions)
                       for i, sess in enumerate(blist_copy)]

        # Optionally, wait for all futures to complete if you need synchronization
        for future in futures:
            future.result()  # This will re-raise any exceptions caught during the session killings
            deleted += 1
            print(f"Deleting {deleted}/{total_sessions}")

        exit(0)

    @classmethod
    @load_stack_decorator
    def get_bastions(cls) -> tuple:
        return tuple(cls.__dry_stack)
