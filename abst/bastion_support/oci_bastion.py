import datetime
import json
import logging
import os
import signal
import subprocess
from json import JSONDecodeError
from pathlib import Path
from shlex import quote as shlex_quote
from time import sleep
from typing import Optional

import oci
import rich
from bext import title
from oci.exceptions import ServiceError

from abst.config import default_creds_path, \
    default_contexts_location, default_conf_path, \
    default_conf_contents, get_public_key, default_parallel_sets_location, broadcast_shm_name
from abst.sharing.local_broadcast import LocalBroadcast
from abst.utils.misc_funcs import run_once
from abst.wrappers import mark_on_exit


class Bastion:
    stopped = False
    session_list = []
    session_desc = dict()
    custom_ssh_options: str = "-o ServerAliveInterval=20"
    force_ssh_options: str = "-o StrictHostKeyChecking=no -o ServerAliveInterval=20 -o UserKnownHostsFile=/dev/null"

    def __init__(self, context_name=None, region=None, direct_json_path=None):
        """

        @param context_name:
        @param region:
        @param direct_json_path:
        """
        self.bid: Optional[str] = None
        self.context_name = context_name
        self.region = region
        self.shell: bool = False
        self.tries: int = 10
        self.connected: bool = False
        self.active_tunnel: subprocess.Popen = Optional[None]
        self.response: Optional[dict] = None
        self._current_status = None
        self.direct_json_path = direct_json_path
        self.__mark_used__(direct_json_path)

        self.lb = LocalBroadcast(broadcast_shm_name)
        self.lb.store_json(context_name, {"region": self.region})

    def __mark_used__(self, path: Optional[Path] = None):
        if path is None:
            cfg_path = Bastion.get_creds_path_resolve(self.context_name)
        else:
            cfg_path = path

        context_cfg = Bastion.load_json(cfg_path)
        context_cfg["last-time-used"] = datetime.datetime.now().isoformat()
        Bastion.write_creds_json(context_cfg, cfg_path)

    @property
    def current_status(self):
        return self._current_status

    @current_status.setter
    def current_status(self, value):
        self._current_status = value
        self.lb.store_json(self.context_name, {"status": value})

    def get_bastion_state(self) -> dict:
        session_id = self.response["id"]
        config = oci.config.from_file()
        if self.region:
            config["region"] = self.region

        req = oci.bastion.BastionClient(config).get_session(session_id)

        try:
            return Bastion.parse_response(req.data)
        except JSONDecodeError:
            rich.print(f"Failed to decode json: '{req.status} {req.data}'")

    def get_print_name(self):
        return self.context_name if self.context_name else "default"

    def kill(self):
        rich.print(f"[red]Killing Bastion {self.get_print_name()} SSH Tunnel[/red]")
        try:
            Bastion.stopped = True
            sess_id = self.response["id"]
            Bastion.session_list.remove(sess_id)
            region = Bastion.session_desc.pop(sess_id)
            print(f"Cleaning {self.get_print_name()}")
            self.delete_bastion_session(sess_id, region)
            print(f"Preparing to remove session {self.get_print_name()}")
            self.active_tunnel.send_signal(signal.SIGTERM)
        except Exception:
            rich.print(f"[green]Bastion successfully deleted[/green] {self.get_print_name()}")
        finally:
            self.lb.delete_context(self.context_name)

    @classmethod
    def delete_bastion_session(cls, sess_id, region=None):
        try:
            config = oci.config.from_file()
            if region:
                config["region"] = region
            while True:
                try:
                    if oci.bastion.BastionClient(config).get_session(
                            sess_id).data.lifecycle_state == "DELETED":
                        return
                    oci.bastion.BastionClient(config).delete_session(sess_id)
                    return
                except ServiceError:
                    sleep(0.1)
        except Exception as ex:
            logging.info(f"Exception while trying to delete session {ex}")

    @mark_on_exit
    def create_managed_loop(self, shell: bool = False):
        Bastion.shell = shell
        print(f"Loading Credentials {self.get_print_name()}")
        creds = self.load_self_creds()
        conf = Bastion.load_config()

        self.current_status = "creating bastion session"
        try:
            res = self.create_bastion_ssh_session_managed(creds)
        except subprocess.CalledProcessError as ex:
            logging.debug(f"Exception {ex}")
            rich.print(f"[red]Invalid Config in abst {self.get_print_name()}[/red]")
            exit(1)

        bid, response = self.load_response(res)

        if bid is None:
            rich.print(
                f"Failed to Create Bastion {self.get_print_name()} with response"
                f" '{response}'")
            self.current_status = "creating bastion session failed"
            return
        else:
            self.current_status = "creating bastion session succeeded"
            self.bid = bid
            rich.print(
                f"Created Session with id '{bid}' on Bastion {self.get_print_name()} "
                f"'{response['bastion_name']}'")

        rich.print("Auto resolving target details from response")
        host = creds["host"]
        target_details = response["target_resource_details"]
        ip = target_details["target_resource_private_ip_address"]
        port = target_details["target_resource_port"]
        private_key_path = creds.get("private-key-path", conf.get("private-key-path",
                                                                  "No supplied private key"))
        user_custom_options = creds.get("ssh-custom-arguments", "")

        if private_key_path == "No supplied private key":
            rich.print("[red]No private key in credentials and config specified[/red]")
            exit(1)

        self.current_status = "waiting for session init"
        self.wait_for_prepared()

        sleep(1)  # Precaution init delay

        self.current_status = "digging tunnel"
        ssh_tunnel_args, exit_code = self.run_ssh_tunnel_managed_session(bid, host,
                                                                         str(Path(
                                                                             private_key_path).expanduser().resolve()),
                                                                         creds[
                                                                             "resource-os-username"],
                                                                         ip, port,
                                                                         shell, user_custom_options)
        logging.info(f"SSH tunnel exited with code {exit_code}")
        if exit_code == 0:
            print(f"User requested termination {self.get_print_name()}")
            self.current_status = "terminated by user"
            self.kill()
            return

        while status := (sdata := self.get_bastion_state())[
                            "lifecycle_state"] == "ACTIVE":
            deleted = self.connect_till_deleted(sdata, ssh_tunnel_args, status, shell,
                                                True)

            if deleted:
                print(f"Bastion {self.get_print_name()} Session got deleted")
                self.current_status = "bastion session deleted"
                return

        print(f"SSH Tunnel for {self.get_print_name()} Terminated")
        self.current_status = "ssh tunnel terminated"
        self.kill()

    @mark_on_exit
    def create_forward_loop(self, shell: bool = False, force: bool = False, tries: int = 0):

        from abst.bastion_support.bastion_scheduler import BastionScheduler
        if BastionScheduler.stopped:
            return

        Bastion.shell = shell
        print(f"Loading Credentials for {self.get_print_name()}")
        creds = self.load_self_creds()
        local_port = creds.get("local-port", 22)
        username = creds.get("resource-os-username", None)
        if username:
            self.lb.store_json(self.context_name, {"port": local_port, "username": username})
        else:
            rich.print(
                "[yellow]No username in context json, please "
                "specify resource-os-username for abst ssh to work[/yellow]")

        title(f'{self.get_print_name()}:{local_port}')

        self.current_status = "creating bastion session"

        try:
            host, ip, port, ssh_pub_key_path, res = self.create_bastion_forward_port_session(
                creds)
        except subprocess.CalledProcessError as ex:
            logging.debug(f"Exception {ex}")
            rich.print(f"[red]Invalid Config in abst[/red]")
            exit(1)

        bid, response = self.load_response(res)

        if bid is None:
            self.current_status = "creating bastion session failed"
            rich.print(f"Failed to Create Bastion {self.get_print_name()}"
                       f" with response '{response}'")
            if tries < 3:
                rich.print("Will try again in 1 second...")
                sleep(1)
                return self.create_forward_loop(shell, force, tries + 1)
            else:
                rich.print(f"Failed to create bastion {tries=}, please try to restart abst")
                exit(1)
        else:
            self.current_status = "creating bastion session succeeded"
            self.bid = bid
            rich.print(f"Created Session for {self.get_print_name()} with id '{bid}'")

        self.current_status = "waiting for session init"

        self.wait_for_prepared()

        sleep(1)  # Precaution

        self.current_status = "digging tunnel"

        user_custom_args = creds.get("ssh-custom-arguments", "")
        ssh_tunnel_arg_str = self.run_ssh_tunnel_port_forward(bid, host, ip, port,
                                                              shell,
                                                              local_port,
                                                              ssh_pub_key_path, force, user_custom_args)

        while status := (sdata := self.get_bastion_state())[
                            "lifecycle_state"] == "ACTIVE" and \
                        not BastionScheduler.stopped:
            deleted = self.connect_till_deleted(sdata, ssh_tunnel_arg_str, status, shell)

            if deleted:
                print(f"Bastion Session {self.get_print_name()} got deleted")
                self.current_status = "bastion session deleted"
                return

        print(f"SSH Tunnel for {self.get_print_name()} Terminated")
        self.current_status = "ssh tunnel terminated"
        self.kill()

    def run_ssh_tunnel_managed_session(self, bid, host, private_key_path, username,
                                       ip, port,
                                       shell, custom_user_options: str = ""):
        if custom_user_options:
            print(
                "[yellow][WARNING] Having custom ssh arguments can prevent your ssh command from working[/yellow]")

        print(f"Bastion {self.get_print_name()} initialized")
        print(f"Initializing SSH Tunnel for {self.get_print_name()}")

        ssh_tunnel_arg_str = (f'ssh -i {private_key_path} {self.custom_ssh_options} {custom_user_options} '
                              f'-o ProxyCommand="ssh -i {private_key_path} -W %h:%p -p {port} {bid}@{host} -A" -p {port} '
                              f'{username}@{ip} -A')
        logging.info(f"Running ssh command {ssh_tunnel_arg_str}")
        exit_code = self.__run_ssh_tunnel_call(ssh_tunnel_arg_str, shell,
                                               already_split=True)
        logging.info(f"SSH command exit code {exit_code}")
        return ssh_tunnel_arg_str, exit_code

    def run_ssh_tunnel_port_forward(self, bid, host, ip, port, shell, local_port,
                                    ssh_pub_key_path, force=False, custom_user_options: str = ""):
        if custom_user_options:
            print(
                "[yellow][WARNING] Having custom ssh arguments can prevent your ssh command from working[/yellow]")

        print(f"Bastion {self.get_print_name()} initialized")
        print(f"Initializing SSH Tunnel for {self.get_print_name()}")
        additional_args = "" if not force else self.force_ssh_options

        ssh_tunnel_arg_str = (
            f"ssh {self.custom_ssh_options} {custom_user_options} -N -L {local_port}:{ip}:{port} -p 22 {bid}@{host} "
            f"-vvv -i {ssh_pub_key_path.strip('.pub')} {additional_args}")
        logging.info(f"Running ssh command {ssh_tunnel_arg_str}")
        exit_code = self.__run_ssh_tunnel(ssh_tunnel_arg_str, shell)
        logging.info(f"SSH command exit code {exit_code}")
        return ssh_tunnel_arg_str

    def wait_for_prepared(self):
        print(f"Waiting for Bastion {self.get_print_name()} to initialize")
        while self.get_bastion_state()["lifecycle_state"] != "ACTIVE":
            sleep(0.5)

    @classmethod
    def parse_response(cls, res):
        return json.loads(str(res))

    def load_response(self, res):
        response = None
        bid = None
        try:
            self.response = response = Bastion.parse_response(res)
            logging.debug(f"Server Response: {response}")
            bid = response.get("id", None)
        except JSONDecodeError as e:
            rich.print(f"Failed to decode json: {res}")
            logging.error(f"Exception {e}")

        return bid, response

    def create_bastion_forward_port_session(self, creds):
        ssh_pub_path = Bastion.init_session_details(creds)

        res = self.__create_bastion_session_port_forward(creds["bastion-id"],
                                                         creds["target-ip"],
                                                         f'{creds["default-name"]}-ctx-'
                                                         f'{self.get_print_name()}',
                                                         int(creds["target-port"]),
                                                         ssh_pub_path,
                                                         int(creds["ttl"]), False,
                                                         creds.get("region", None))
        try:
            trs = Bastion.parse_response(res)
            Bastion.session_list.append(trs["id"])
            Bastion.session_desc[trs["id"]] = creds.get("region", None)
            logging.debug(f"Added session id of {self.context_name}")
        except Exception as e:
            logging.error(f"Exception {e}")
        return creds["host"], creds["target-ip"], creds["target-port"], ssh_pub_path, res

    @classmethod
    def init_session_details(cls, creds):
        cfg = Bastion.load_config()
        if "region" not in creds.keys():
            rich.print("Missing region, will use profile default")
            rich.print("If you want to add region, run abst config upgrade <ctx-name>")

        ssh_pub_path = str(Path(creds.get("ssh-pub-path",
                                          cfg.get("ssh-pub-path",
                                                  "No Public key supplied"))).expanduser().resolve())

        if ssh_pub_path == "No Public key supplied":
            rich.print(
                "[red]No public key in credentials and config specified[/red]")
            exit(1)
        if not Path(ssh_pub_path).exists():
            rich.print("[red]SSH key has invalid path[/red]")
            exit(1)
        return ssh_pub_path

    def create_bastion_ssh_session_managed(self, creds):
        ssh_pub_path = Bastion.init_session_details(creds)

        try:
            res = self.__create_bastion_ssh_session_managed(creds["bastion-id"],
                                                            creds["resource-id"],
                                                            f'{creds["default-name"]}-ctx-'
                                                            f'{self.get_print_name()}',
                                                            creds["resource-os-username"],
                                                            ssh_pub_path,
                                                            int(creds["ttl"]), False,
                                                            creds.get("region", None)
                                                            )
            try:
                trs = Bastion.parse_response(res)
                Bastion.session_list.append(trs["id"])
                Bastion.session_desc[trs["id"]] = creds.get("region", None)
                logging.debug(f"Added session id of {self.context_name}")
            except Exception as e:
                logging.error(f"Exception {e}")
            return res
        except KeyError as ex:
            rich.print(f"Missing filled out parameter for '{self.get_print_name()}' {ex}")
            exit(1)

    @classmethod
    def get_contexts(cls) -> dict:
        out = dict()
        for context in default_contexts_location.iterdir():
            with open(context, "r") as f:
                out[context.name.replace(".json", "")] = json.load(f)

        return out

    @classmethod
    def get_creds_path_resolve(cls, context_name) -> Path:
        if context_name is None or context_name == "default":
            return default_creds_path
        else:
            return default_contexts_location / (context_name + ".json")

    def get_creds_path(self) -> Path:
        if self.direct_json_path:
            return self.direct_json_path
        elif self.context_name is None:
            return default_creds_path
        else:
            return default_contexts_location / (self.context_name + ".json")

    def load_self_creds(self):
        try:
            return self.load_json(self.get_creds_path())
        except FileNotFoundError:
            td = self.generate_sample_dict()

            creds_path = self.write_creds_json(td, self.get_creds_path())

            rich.print(
                f"Sample credentials generated, please fill 'creds.json' in {creds_path}"
                f" with "
                f"your credentials for this to work")
            exit(1)

    @classmethod
    def load_config(cls):
        return cls.load_json(default_conf_path)

    @classmethod
    def load_json(cls, path=default_creds_path) -> dict:
        if not path.name.endswith(".json"):
            logging.error(f"File is not json!")
            return {}

        if not default_conf_path.exists() and path == default_conf_path:
            default_conf_path.parent.mkdir(exist_ok=True)
            with open(str(path), "w") as f:
                json.dump(
                    {"last-check": datetime.datetime.timestamp(datetime.datetime.now())},
                    f, indent=3)
        try:
            with open(str(path), "r") as f:
                creds = json.load(f)
                if isinstance(creds, str):
                    logging.error(f"Failed to load creds {path} content is loaded as string")
                    return {}
                if "delete_this" in creds.keys():
                    rich.print(
                        f"[red]'Delete This' Tag not removed! Please Remove it in {path} "
                        f"before continuing[/red]")
                    exit(1)
                logging.debug(f"Loaded Credentials {creds}")
        except JSONDecodeError:
            logging.error(f"Failed to load json {path}")
            return {}
        return creds

    @classmethod
    def create_default_locations(cls):
        Path(default_creds_path.parent).mkdir(exist_ok=True)
        Path(default_contexts_location).mkdir(exist_ok=True)
        Path(default_parallel_sets_location).mkdir(exist_ok=True)

        if not default_conf_path.exists():
            cls.write_creds_json(default_conf_contents, default_conf_path)
        else:
            something_changed = False
            data = Bastion.load_config()
            for key, value in default_conf_contents.items():
                if key not in data.keys():
                    data[key] = value
                    something_changed = True
            if something_changed:
                cls.write_creds_json(default_conf_contents, default_conf_path)
                rich.print("[green]Updated .abst/config file[/green]")

    @classmethod
    def write_creds_json(cls, td: dict, path: Path):

        if not path.name.endswith(".json"):
            # Construct new filename with .json extension
            tmp_path = path.with_suffix(".json")
        else:
            tmp_path = path

        with open(str(tmp_path), "w") as f:
            json.dump(td, f, indent=4)
        return path

    def connect_till_deleted(self, sdata, ssh_tunnel_arg_str, status, shell,
                             already_split=False):
        """
        Will connect to session and reconnect every time it disconnects until session is
        deleted :param shell: If you use shell environment (can have different impacts on
        MAC and LINUX) :param sdata: :param ssh_tunnel_arg_str: param status: :return:
        """
        from abst.bastion_support.bastion_scheduler import BastionScheduler

        for i in range(1, 3):
            if not status and not BastionScheduler.stopped:
                rich.print(f"({self.get_print_name()}) Trying another time {i}/3")
                status = self.__run_ssh_tunnel(ssh_tunnel_arg_str, shell, already_split)
            else:
                break

        # Proceed with check for disconnect or termination, after process termination
        if not self.connected and status and not BastionScheduler.stopped:
            rich.print(
                f"Checking for idle termination, Bastion {self.get_print_name()} "
                f"Active? {status}")
            created_time = datetime.datetime.fromisoformat(
                sdata["time_created"]).astimezone(
                datetime.timezone.utc)
            now_time = datetime.datetime.now(datetime.timezone.utc)
            ttl_now = now_time - created_time
            ttl_max = sdata["session_ttl_in_seconds"]
            delta = ttl_max - ttl_now.seconds
            if delta > 0 and not BastionScheduler.stopped and not Bastion.stopped:
                print(
                    f"Bastion {self.get_print_name()} "
                    f"Current session {delta} seconds remaining ({ttl_now}) "
                    f"reconnecting")
                self.__run_ssh_tunnel(ssh_tunnel_arg_str, shell, already_split)
                return False
            else:
                print(
                    f"Bastion {self.get_print_name()} "
                    f"Session TTL run out, please start create new one")
                return True

    @classmethod
    def __create_bastion_session_port_forward(cls, bastion_id, ip, name, port: int,
                                              ssh_path,
                                              ttl: int, shell, region: Optional[str]):
        public_key = get_public_key(ssh_path)
        sess_details = oci.bastion.models.CreateSessionDetails(bastion_id=bastion_id,
                                                               target_resource_details=oci.bastion.models.CreatePortForwardingSessionTargetResourceDetails(
                                                                   session_type="PORT_FORWARDING",
                                                                   target_resource_private_ip_address=ip,
                                                                   target_resource_port=port),
                                                               key_details=oci.bastion.models.PublicKeyDetails(
                                                                   public_key_content=public_key),
                                                               display_name=name,
                                                               key_type="PUB",
                                                               session_ttl_in_seconds=ttl)
        config = oci.config.from_file()
        # Overriding region from user profile
        if region:
            config["region"] = region

        print("Creating Port Forward Session")
        if not cls.stopped:
            req = oci.bastion.BastionClient(config).create_session(sess_details)
            logging.debug(f"{req.data} Status: {req.status}")
        else:
            return None
        return req.data

    @classmethod
    def __create_bastion_ssh_session_managed(cls, bastion_id, resource_id, name,
                                             os_username, ssh_path, ttl, shell,
                                             region: Optional[str]):
        if Bastion.stopped:
            return
        public_key = get_public_key(ssh_path)
        sess_details = oci.bastion.models.CreateSessionDetails(bastion_id=bastion_id,
                                                               target_resource_details=oci.bastion.models.CreateManagedSshSessionTargetResourceDetails(
                                                                   session_type="MANAGED_SSH",
                                                                   target_resource_id=resource_id,
                                                                   target_resource_operating_system_user_name=os_username),
                                                               key_details=oci.bastion.models.PublicKeyDetails(
                                                                   public_key_content=public_key),
                                                               display_name=name,
                                                               key_type="PUB",
                                                               session_ttl_in_seconds=ttl)
        config = oci.config.from_file()

        if region:
            config["region"] = region

        req = oci.bastion.BastionClient(config).create_session(sess_details)

        print("Creating Managed SSH Session")
        logging.debug(f"{req.data} Status: {req.status}")
        return req.data

    @classmethod
    def get_ssh_pub_key_path(cls, creds):
        cfg = Bastion.load_config()
        ssh_pub_path = creds.get("ssh-key-path",
                                 cfg.get("ssh-pub-path", "No Public key supplied"))

        if ssh_pub_path == "No Public key supplied":
            rich.print(
                "[red]No public key in credentials and config specified[/red]")
            exit(1)
        return str(Path(ssh_pub_path).expanduser().resolve())

    @classmethod
    def generate_sample_dict(cls):
        td = dict()
        td["host"] = "host.bastion.us-phoenix-1.oci.oraclecloud.com"
        td["bastion-id"] = "ocid1.bastion......"
        td["default-name"] = "My super cool name"
        td["ssh-pub-path"] = str((Path().home() / ".ssh" / "id_rsa.pub").absolute())
        td["private-key-path"] = str((Path().home() / ".ssh" / "id_rsa").absolute())
        td["target-ip"] = "0.0.0.0 // This is required only for Port Forward session"
        td["local-port"] = "22"
        td["target-port"] = "22 // This is required only for Port Forward session"
        td["ttl"] = "3600"
        td["resource-id"] = "ocid... " \
                            "// This is required only for Managed SSH session"
        td["resource-os-username"] = "MyResourceName " \
                                     "// This is required only for Managed SSH session"
        td["private-key-path"] = "Path to private key used in SSH Tunnel " \
                                 "// This is required only for Managed SSH session"
        return td

    def process_args(self, already_split, shell, ssh_tunnel_arg_str):
        if not already_split and not shell:
            args_split = ssh_tunnel_arg_str.split()
        elif not already_split and shell:
            args_split = ssh_tunnel_arg_str
        else:
            if shell:
                args_split = " ".join(ssh_tunnel_arg_str)
            else:
                args_split = ssh_tunnel_arg_str
        logging.debug(
            f'({self.get_print_name()}) SSH Tunnel command: '
            f'{" ".join(args_split) if not shell else args_split}')
        return args_split

    def __run_ssh_tunnel_call(self, ssh_tunnel_arg_str, shell, already_split=False):

        return os.system(shlex_quote(ssh_tunnel_arg_str))

    def __run_ssh_tunnel(self, ssh_tunnel_arg_str, shell, already_split=False):
        """

        :param ssh_tunnel_arg_str: String for ssh tunnel creation
        :param shell: If you use shell environment (can have different impacts on MAC and
         LINUX)
        :return:
        """
        args_split = self.process_args(already_split, shell, ssh_tunnel_arg_str)
        try:
            p = subprocess.Popen(args_split, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, shell=shell)
        except FileNotFoundError:
            self.connected = False
            rich.print(
                "Failed to establish SSH tunnel due to different setting os shell terminal, [red]try to run "
                "again with --shell[/red]")
            return True

        self.active_tunnel = p
        while p.poll() is None and self.tries >= 0:
            line = p.stdout.readline().decode("utf-8").strip()
            line_err = None

            if p.stderr:
                line_err = p.stderr.readline().decode("utf-8").strip()

            if line:
                logging.debug(f"({self.get_print_name()}) SSH stdout: {line}")
            if line_err:
                logging.debug(f"({self.get_print_name()}) SSH stderr: {line_err}")

            if "Permission denied" in line:
                self.connected = False
                return False
            if "pledge:" in line:
                self.print_succeeded()
                self.connected = True
                self.current_status = "connected"
                self.tries = 10

            if not line and not line_err:
                sleep(0.1)

        logging.debug(f"({self.get_print_name()}) Waiting for ssh tunnel to end")
        p.wait()
        logging.debug(
            f"({self.get_print_name()}) SSH Tunnel Process ended with exit code "
            f"{p.returncode}")

        if p.returncode == 255:
            rich.print(
                f"({self.get_print_name()}) "
                f"SSH Tunnel can not be initialized because of failed authorization")
            rich.print(
                f"({self.get_print_name()}) "
                f"Please check you configuration, for more info use --debug flag")
            if self.tries <= 0:
                rich.print(
                    "[red]If this continues to happen without connection it can be because ip changed in ["
                    "yellow]~/.ssh/known_hosts[/yellow], delete it and"
                    " try again[/red]")
                self.kill()
                self.current_status = "Failed"
                exit(255)
            else:
                self.tries -= 1
                self.current_status = f"failed {self.tries} left"
        self.connected = False
        return True

    @run_once
    def print_succeeded(self):
        rich.print(f"({self.get_print_name()}) Success !")
        rich.print(
            f"({self.get_print_name()}) SSH Tunnel Running from "
            f"{datetime.datetime.now()}")
