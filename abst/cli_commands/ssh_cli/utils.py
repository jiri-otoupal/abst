import os

import rich


def filter_keys_by_substring(dictionary: dict, substring: str) -> list:
    # Convert substring to lower a case for case-insensitive comparison
    substring_lower = substring.lower()
    # Use a comprehension to filter keys
    filtered_keys = [key for key in dictionary.keys() if substring_lower in key.lower()]
    return filtered_keys


def filter_keys_by_port(data: dict, port: int):
    """Filter and return keys from the servers dictionary where the port matches the given input."""
    return [key for key, data in data.items() if port in str(data.get('port', None))]


def do_ssh(context_name: str, username, port):
    rich.print(f"[green]Running SSH to {context_name}[/green] "
               f"[yellow]{username}@localhost:{port}[/yellow]")
    os.system(f'ssh {username}@127.0.0.1 -p {port}')
