import rich
from InquirerPy import inquirer

from abst.config import default_conf_path


def helm_login_dialog():
    rich.print(f"Please Fill in Repository details that"
               f" are going to be saved in {default_conf_path}")
    host = inquirer.text("Host", default="phx.ocir.io").execute()
    remote = inquirer.text("Remote URL", default="oci://").execute()
    username = inquirer.text("Username").execute()
    password = inquirer.secret("Password").execute()
    return host, password, remote, username
