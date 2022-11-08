from threading import Thread
from time import sleep

import rich
from click import clear

from abst.config import default_stack_location, default_stack_contents, \
    default_contexts_location
from abst.oci_bastion import Bastion
from abst.wrappers import load_stack_decorator


class BastionScheduler:
    __dry_stack = set()
    __live_stack = set()

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
    @load_stack_decorator
    def add_bastion(cls, context_name: str):

        if context_name in cls.__dry_stack:
            print("Already in stack")
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
    def __display(cls):
        for bastion in cls.__live_stack:
            conf = bastion.load_self_creds()
            active = bastion.connected and bastion.active_tunnel
            color = {'green' if active else 'orange'}
            rich.print(
                f"Bastion: [green]{bastion.context_name}[/green] "
                f"Local Port: [red]{conf.get('local-port', 'Not Specified')}[/red]"
                f"Active: [{color}]{active}[/{color}]")

    @classmethod
    def __display_loop(cls):
        while True:
            clear()
            cls.__display()
            sleep(3)

    @classmethod
    @load_stack_decorator
    def run(cls):
        rich.print("Will run all Bastions in parallel")
        thread_list = []

        for context_name in cls.__dry_stack:
            bastion = Bastion(context_name)
            cls.__live_stack.add(bastion)
            t = Thread(name=context_name, target=bastion.create_forward_loop, daemon=True)
            thread_list.append(t)
            t.start()
            rich.print(f"Started {context_name}")

        Thread(name="Display", target=cls.__display_loop, daemon=True).start()

        for t in thread_list:
            if t.is_alive():
                t.join()

        rich.print("All Bastion threads died")

    @classmethod
    @load_stack_decorator
    def local_port_in_stack(cls, context_name: str):
        instance_creds = Bastion.load_json(default_contexts_location /
                                           (context_name + ".json"))
        for bastion in cls.__dry_stack:
            b_creds = bastion.load_self_creds()
            if b_creds["local-port"] == instance_creds["local-port"]:
                return True, bastion
        return False, None

    @classmethod
    def kill_all(cls, a=None, b=None, c=None):
        # This should be only executed in running state
        for bastion in cls.__live_stack:
            bastion.kill()

    @classmethod
    @load_stack_decorator
    def get_bastions(cls) -> tuple:
        return tuple(cls.__dry_stack)
