"""
__version__.py
~~~~~~~~~~~~~~

Information about the current version of the py-package-template package.
"""

__title__ = "abst"
__description__ = (
    "CLI Command making OCI Bastion and kubernetes usage simple and fast"
)

__version__ = "2.3.28"
__author__ = "Jiri Otoupal"
__author_email__ = "jiri-otoupal@ips-database.eu"
__license__ = "MIT"
__url__ = "https://github.com/jiri-otoupal/abst"
__pypi_repo__ = "https://pypi.org/project/abst/"

__version_name__ = "Formatted-Merged Giraffe"
__change_log__ = """
* Added new option to context config so user can input custom ssh arguments to 'ssh-custom-arguments' key in context\n
* Listing context will show last usage time\n
* Changed formatting of 'abst context list' and 'abst parallel list'\n
* Merged Config to Context group
"""
