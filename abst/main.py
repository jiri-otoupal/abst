import datetime
import json
import logging
import signal
import subprocess
from json import JSONDecodeError
from pathlib import Path
from time import sleep

import click

default_creds_path = (Path().home().resolve() / "creds.json").absolute()


class Bastion:
    connected: bool = False
    active_tunnel: subprocess.Popen = None
    response: dict = None

    @classmethod
    def get_bastion_state(cls) -> dict:
        bastion_id = cls.response["data"]["id"]
        get_state_arg_str = f"oci bastion session get --session-id {bastion_id}"
        res = subprocess.check_output(get_state_arg_str.split())
        try:
            return json.loads(res)
        except JSONDecodeError:
            print(f"Failed to decode json: {res}")

    @classmethod
    def kill_bastion(cls, a=None, b=None, c=None):
        print("Killing Bastion SSH Tunnel")
        cls.active_tunnel.send_signal(signal.SIGTERM)
        sess_id = cls.response["data"]["id"]
        print("Cleaning")
        print("Removing Bastion session")
        bastion_kill_arg_str = f"oci bastion session delete --session-id {sess_id}  --force"
        out = subprocess.check_output(bastion_kill_arg_str.split(), shell=True)
        print(out.decode("utf-8"))
        print("Removed Session")
        exit(0)

    @classmethod
    def create_bastion(cls):
        print("Loading Credentials")
        try:
            with open(str(default_creds_path), "r") as f:
                creds = json.load(f)
                if "delete_this" in creds.keys():
                    raise FileNotFoundError()
        except FileNotFoundError:
            td = dict()
            td["delete_this"] = "Delete This Key after you Fill this file with your credentials"
            td["host"] = "host.bastion.us-phoenix-1.oci.oraclecloud.com"
            td["bastion-id"] = "ocid1.bastion......"
            td["default-name"] = "My super cool name"
            td["ssh-pub-path"] = "~/.ssh/id_rsa.pub"
            td["target-ip"] = "0.0.0.0"
            td["target-port"] = "22"
            td["ttl"] = "1800"

            creds_path = default_creds_path
            if not creds_path.exists():
                with open(str(creds_path), "w") as f:
                    json.dump(td, f, indent=4)

            print(
                f"Sample credentials generated, please fill 'creds.json' in {creds_path} with "
                f"your credentials for this to work")
            exit(1)

        host = creds["host"]
        bastion_id = creds["bastion-id"]
        name = creds["default-name"]
        ssh_path = str(Path(creds["ssh-pub-path"]).resolve().absolute())
        ip = creds["target-ip"]
        port = creds["target-port"]
        ttl = creds["ttl"]

        bastion_arg_str = f"oci bastion session create-port-forwarding " \
                          f"--bastion-id {bastion_id} " \
                          f"--display-name {name} " \
                          f"--ssh-public-key-file {ssh_path} " \
                          f"--key-type PUB " \
                          f"--target-private-ip {ip} " \
                          f"--target-port {port}" \
                          f" --session-ttl {ttl}"
        print("Creating Session")
        res = subprocess.check_output(bastion_arg_str.split(), shell=True)
        try:
            cls.response = response = json.loads(res)
        except JSONDecodeError:
            print(f"Failed to decode json: {res}")

        bid = response.get("data", None).get("id", None)

        if bid is None:
            print(f"Failed to Create Bastion with response {response}")
            return
        else:
            print(f"Created Session with id {bid}")

        ssh_tunnel_arg_str = f"ssh  -N -L {port}:{ip}:{port} -p 22 {bid}@{host} -v"
        print("Waiting for bastion to initialize")

        while cls.get_bastion_state()["data"]["lifecycle-state"] != "ACTIVE":
            sleep(1)

        sleep(1)  # Precaution

        print("Bastion initialized")
        print("Initializing SSH Tunnel")
        cls.ssh_tunnel(ssh_tunnel_arg_str)

        while status := (sdata := cls.get_bastion_state()["data"])["lifecycle-state"] == "ACTIVE":
            for i in range(1, 3):
                if not status:
                    print(f"Trying another time {i}/3")
                    status = cls.ssh_tunnel(ssh_tunnel_arg_str)
                else:
                    break
            if not cls.connected and status:
                print(f"Checking for idle termination, Bastion Active? {status}")
                created_time = datetime.datetime.fromisoformat(sdata["time-created"]).astimezone(
                    datetime.timezone.utc)
                now_time = datetime.datetime.now(datetime.timezone.utc)
                ttl_now = now_time - created_time
                ttl_max = sdata["session-ttl-in-seconds"]
                delta = ttl_max - ttl_now.seconds
                if delta > 0:
                    print(
                        f"Current session {delta} seconds remaining ({ttl_now}) "
                        f"reconnecting")
                    cls.ssh_tunnel(ssh_tunnel_arg_str)
                else:
                    print("Bastion Session TTL run out, please start create new one")

        print("SSH Tunnel Terminated")
        Bastion.kill_bastion()

    @classmethod
    def ssh_tunnel(cls, ssh_tunnel_arg_str):
        p = subprocess.Popen(ssh_tunnel_arg_str.split(), stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, shell=True)
        cls.active_tunnel = p
        while not p.poll():
            line = p.stdout.readline().decode("utf-8").replace("\r", "").replace("", "")
            if "Permission denied" in line:
                cls.connected = False
                return False
            if "pledge: network" in line:
                print("Success !")
                print(f"SSH Tunnel Running from {datetime.datetime.now()}")
                cls.connected = True
            if line:
                logging.debug(line)
        cls.connected = False
        return True


# Press the green button in the gutter to run the script.
def main():
    cli()


@click.group()
def cli():
    pass


@cli.command("create")
def create():
    signal.signal(signal.SIGINT, Bastion.kill_bastion)
    signal.signal(signal.SIGTERM, Bastion.kill_bastion)
    Bastion.create_bastion()


# See PyCharm help at https://www.jetbrains.com/help/pycharm/

if __name__ == '__main__':
    cli()
