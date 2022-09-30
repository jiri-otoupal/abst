# Auto Bastion

Manage your bastion sessions automatically without
pain of creating them by clicking and copy pasting commands

[![image](https://img.shields.io/pypi/v/abst.svg)](https://pypi.org/project/dvpn/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/abst)](https://pypi.org/project/abst/)
[![Downloads](https://pepy.tech/badge/abst)](https://pepy.tech/project/abst)

### Supported

#### OS

No specific requirements here, whatever runs Python

#### Cloud Providers

* **Oracle Cloud**

## Requirements

### Python

* 3.7+

### OCI CLI

This package needs oci cli installed to function
Tutorial on Installation

* https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm

#### Configuration of OCI CLI

* Add key in your Oracle cloud profile
* Generate new key
* Copy configuration file generated in your profile to `~/.oci/config`
* Replace path of your `*.pem` key on line with **#TODO**


## Installing

### MacOS
On most MacOS machines there is `pip3` instead of `pip` **use pip3 for install**

Install and update using [pip](https://pip.pypa.io/en/stable/quickstart/):

```bash
pip install abst

or

pip3 install abst
```

## How to set up

* Use `abst config fill` to fill your credentials for usage, you can find all the credentials on
  cloud provider site

## Usage

###### Both commands do automatic reconnect on idle SSH Tunnel termination

* `abst create forward/managed single` for single bastion session with persisting SSH connection
* `abst create forward/managed fullauto` for automatic Bastion session creation once deleted, will keep your
  connection alive till you kill this script
* `abst clean` for removal all the saved credentials

<hr>
Did I made your life less painfull ? 
<br>
<br>
Support my coffee addiction ;)
<br>
<a href="https://www.buymeacoffee.com/jiriotoupal" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy me a Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>
