import datetime
import json
import logging
import signal
import subprocess
from json import JSONDecodeError
from pathlib import Path
from time import sleep

import rich

from abst.config import default_creds_path


class Bastion:
    shell: bool = False
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
            rich.print(f"Failed to decode json: '{res}'")

    @classmethod
    def kill_bastion(cls, a=None, b=None, c=None):
        print("Killing Bastion SSH Tunnel")
        try:
            cls.active_tunnel.send_signal(signal.SIGTERM)
            sess_id = cls.response["data"]["id"]
            print("Cleaning")
            out = cls.delete_bastion_session(sess_id, Bastion.shell)
            rich.print(out)
            print("Removed Session")
        except Exception:
            print("Looks like Bastion is already deleted")
        finally:
            exit(0)

    @classmethod
    def delete_bastion_session(cls, sess_id, shell):
        print("Removing Bastion session")
        bastion_kill_arg_str = f"oci bastion session delete --session-id {sess_id}" \
                               f" --force"
        out = subprocess.check_output(bastion_kill_arg_str.split(), shell=shell).decode(
            "utf-8")
        return out

    @classmethod
    def create_managed_loop(cls, shell: bool = False):
        Bastion.shell = shell
        print("Loading Credentials")
        creds = cls.handle_creds_load()

        res = cls.create_bastion_ssh_session_managed(creds, shell)

        bid, response = cls.load_response(res)

        if bid is None:
            rich.print(f"Failed to Create Bastion with response '{response}'")
            return
        else:
            rich.print(
                f"Created Session with id '{bid}' on Bastion '{response['data']['bastion-name']}'")

        rich.print("Auto resolving target details from response")
        host = creds["host"]
        target_details = response["data"]["target-resource-details"]
        ip = target_details["target-resource-private-ip-address"]
        port = target_details["target-resource-port"]

        cls.wait_for_prepared()

        sleep(1)  # Precaution

        ssh_tunnel_args = cls.run_ssh_tunnel_managed_session(bid, host,
                                                             creds["private-key-path"],
                                                             creds["resource-os-username"],
                                                             ip, port,
                                                             shell)

        while status := (sdata := cls.get_bastion_state()["data"])["lifecycle-state"] == "ACTIVE":
            deleted = cls.connect_till_deleted(sdata, ssh_tunnel_args, status, shell, True)

            if deleted:
                print("Bastion Session got deleted")
                return

        print("SSH Tunnel Terminated")
        Bastion.kill_bastion()

    @classmethod
    def create_forward_loop(cls, shell: bool = False):
        Bastion.shell = shell
        print("Loading Credentials")
        creds = cls.handle_creds_load()

        host, ip, port, res = cls.create_bastion_forward_port_session(creds,
                                                                      shell)

        bid, response = cls.load_response(res)

        if bid is None:
            rich.print(f"Failed to Create Bastion with response '{response}'")
            return
        else:
            rich.print(f"Created Session with id '{bid}'")

        cls.wait_for_prepared()

        sleep(1)  # Precaution

        ssh_tunnel_arg_str = cls.run_ssh_tunnel_port_forward(bid, host, ip, port,
                                                             shell)

        while status := (sdata := cls.get_bastion_state()["data"])[
                            "lifecycle-state"] == "ACTIVE":
            deleted = cls.connect_till_deleted(sdata, ssh_tunnel_arg_str, status, shell)

            if deleted:
                print("Bastion Session got deleted")
                return

        print("SSH Tunnel Terminated")
        Bastion.kill_bastion()

    @classmethod
    def run_ssh_tunnel_managed_session(cls, bid, host, priv_key_path, username,
                                       ip, port,
                                       shell):
        print("Bastion initialized")
        print("Initializing SSH Tunnel")

        ssh_tunnel_args = [f"ssh", "-i", f"{priv_key_path}", "-o",
                           f"ProxyCommand='ssh -i {priv_key_path} -W %h:%p -p {port} {bid}@{host}'",
                           "-p", f"{port}", f"{username}@{ip}", "-v"]
        cls.__run_ssh_tunnel(ssh_tunnel_args, shell, already_split=True)
        return ssh_tunnel_args

    @classmethod
    def run_ssh_tunnel_port_forward(cls, bid, host, ip, port, shell):
        print("Bastion initialized")
        print("Initializing SSH Tunnel")
        ssh_tunnel_arg_str = f"ssh  -N -L {port}:{ip}:{port} -p 22 {bid}@{host} -v"
        cls.__run_ssh_tunnel(ssh_tunnel_arg_str, shell)
        return ssh_tunnel_arg_str

    @classmethod
    def wait_for_prepared(cls):
        print("Waiting for Bastion to initialize")
        while cls.get_bastion_state()["data"]["lifecycle-state"] != "ACTIVE":
            sleep(1)

    @classmethod
    def load_response(cls, res):
        response = None
        try:
            cls.response = response = json.loads(res)
        except JSONDecodeError:
            print(f"Failed to decode json: {res}")
        bid = response.get("data", None).get("id", None)
        return bid, response

    @classmethod
    def create_bastion_forward_port_session(cls, creds, shell):
        ssh_key_path = cls.get_ssh_pub_key_path(creds)
        res = cls.__create_bastion_session_port_forward(creds["bastion-id"],
                                                        creds["target-ip"],
                                                        creds["default-name"],
                                                        creds["target-port"],
                                                        ssh_key_path,
                                                        creds["ttl"], shell)
        return creds["host"], creds["target-ip"], creds["target-port"], res

    @classmethod
    def create_bastion_ssh_session_managed(cls, creds, shell):
        ssh_key_path = cls.get_ssh_pub_key_path(creds)
        res = cls.__create_bastion_ssh_session_managed(creds["bastion-id"],
                                                       creds["resource-id"],
                                                       creds["default-name"],
                                                       creds["resource-os-username"],
                                                       ssh_key_path,
                                                       creds["ttl"], shell
                                                       )
        return res

    @classmethod
    def handle_creds_load(cls):
        try:
            return cls.load_creds_json()
        except FileNotFoundError:
            td = cls.generate_sample_dict()

            creds_path = cls.write_creds_json(td)

            rich.print(
                f"Sample credentials generated, please fill 'creds.json' in {creds_path}"
                f" with "
                f"your credentials for this to work")
            exit(1)

    @classmethod
    def load_creds_json(cls) -> dict:
        with open(str(default_creds_path), "r") as f:
            creds = json.load(f)
            if "delete_this" in creds.keys():
                raise Exception("Delete This Tag not removed! Please Remove Before continue")
        return creds

    @classmethod
    def create_default_location(cls):
        Path(default_creds_path.parent).mkdir(exist_ok=True)

    @classmethod
    def write_creds_json(cls, td: dict):
        creds_path = default_creds_path
        with open(str(creds_path), "w") as f:
            json.dump(td, f, indent=4)
        return creds_path

    @classmethod
    def connect_till_deleted(cls, sdata, ssh_tunnel_arg_str, status, shell, already_split=False):
        """
        Will connect to session and reconnect every time it disconnect until session is
        deleted :param shell: If use shell environment (can have different impacts on
        MAC and LINUX) :param sdata: :param ssh_tunnel_arg_str: :param status: :return:
        """
        for i in range(1, 3):
            if not status:
                rich.print(f"Trying another time {i}/3")
                status = cls.__run_ssh_tunnel(ssh_tunnel_arg_str, shell, already_split)
            else:
                break
        if not cls.connected and status:
            rich.print(f"Checking for idle termination, Bastion Active? {status}")
            created_time = datetime.datetime.fromisoformat(
                sdata["time-created"]).astimezone(
                datetime.timezone.utc)
            now_time = datetime.datetime.now(datetime.timezone.utc)
            ttl_now = now_time - created_time
            ttl_max = sdata["session-ttl-in-seconds"]
            delta = ttl_max - ttl_now.seconds
            if delta > 0:
                print(
                    f"Current session {delta} seconds remaining ({ttl_now}) "
                    f"reconnecting")
                cls.__run_ssh_tunnel(ssh_tunnel_arg_str, shell, already_split)
                return False
            else:
                print("Bastion Session TTL run out, please start create new one")
                return True

    @classmethod
    def __create_bastion_session_port_forward(cls, bastion_id, ip, name, port, ssh_path,
                                              ttl, shell):
        bastion_arg_str = f"oci bastion session create-port-forwarding " \
                          f"--bastion-id {bastion_id} " \
                          f"--display-name {name} " \
                          f"--ssh-public-key-file {ssh_path} " \
                          f"--key-type PUB " \
                          f"--target-private-ip {ip} " \
                          f"--target-port {port} " \
                          f"--session-ttl {ttl}"
        print("Creating Port Forward Session")
        res = subprocess.check_output(bastion_arg_str.split(), shell=shell)
        return res

    @classmethod
    def __create_bastion_ssh_session_managed(cls, bastion_id, resource_id, name,
                                             os_username, ssh_path, ttl, shell):
        bastion_arg_str = f"oci bastion session create-managed-ssh " \
                          f"--bastion-id {bastion_id} " \
                          f"--display-name {name} " \
                          f"--ssh-public-key-file {ssh_path} " \
                          f"--key-type PUB " \
                          f"--target-resource-id {resource_id} " \
                          f"--target-os-username {os_username} " \
                          f"--session-ttl {ttl}"

        print("Creating Managed SSH Session")
        res = subprocess.check_output(bastion_arg_str.split(), shell=shell)
        logging.debug(res.decode())
        return res

    @classmethod
    def get_ssh_pub_key_path(cls, creds):
        return str(Path(creds["ssh-pub-path"]).expanduser().resolve())

    @classmethod
    def generate_sample_dict(cls, generate_with_delete_this=True):
        td = dict()
        if generate_with_delete_this:
            td["delete_this"] = "Delete This Line after you Fill" \
                                " this file with your credentials"
        td["host"] = "host.bastion.us-phoenix-1.oci.oraclecloud.com"
        td["bastion-id"] = "ocid1.bastion......"
        td["default-name"] = "My super cool name"
        td["ssh-pub-path"] = str((Path().home() / ".ssh" / "id_rsa.pub").absolute())
        td["private-key-path"] = str((Path().home() / ".ssh" / "id_rsa").absolute())
        td["target-ip"] = "0.0.0.0 // This is required only for Port Forward session"
        td["target-port"] = "22 // This is required only for Port Forward session"
        td["ttl"] = "10800"
        td["resource-id"] = "ocid... " \
                            "// This is required only for Managed SSH session"
        td["resource-os-username"] = "MyResourceName " \
                                     "// This is required only for Managed SSH session"
        td["private-key-path"] = "Path to private key used in SSH Tunnel " \
                                 "// This is required only for Managed SSH session"
        return td

    @classmethod
    def __run_ssh_tunnel(cls, ssh_tunnel_arg_str, shell, already_split=False):
        """

        :param ssh_tunnel_arg_str: String for ssh tunnel creation
        :param shell: If use shell environment (can have different impacts on MAC and LINUX)
        :return:
        """
        if not already_split:
            args_split = ssh_tunnel_arg_str.split()
        else:
            args_split = ssh_tunnel_arg_str

        p = subprocess.Popen(args_split, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, shell=shell)
        cls.active_tunnel = p
        while not p.poll():
            line = p.stdout.readline().decode("utf-8").replace("\r", "").replace("", "")

            if "Permission denied" in line:
                cls.connected = False
                return False
            if "pledge:" in line:
                print("Success !")
                rich.print(f"SSH Tunnel Running from {datetime.datetime.now()}")
                cls.connected = True
            if line:
                logging.debug(f"SSH: {line}")
        cls.connected = False
        return True
