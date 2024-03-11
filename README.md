# Auto Bastion

Manage your bastion sessions automatically without
pain of creating them by clicking and copy pasting commands

[![image](https://img.shields.io/pypi/v/abst.svg)](https://pypi.org/project/abst/)
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

#### Configuration of OCI SDK

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

* Use `abst ctx fill {context}` to fill your credentials for usage, you can find all the
  credentials on
  cloud provider site, leave context empty if you want to fill default
* Use `abst ctx generate {context}` to generate default config for context, leave context empty if you
  want to generate to
  default

## Usage

###### Both commands do automatic reconnect on idle SSH Tunnel termination

* `abst create forward/managed {context}` for automatic Bastion session creation once
  deleted, will keep your,
  leave context empty if you want to use default
  connection alive till you kill this script
* `abst do forward/managed {context}` alias for `abst create`
* `abst clean` for removal all the saved credentials
* `abst use {context}` for using different config that you had filled, `default` is the default
  context in `creds.json`
* Use `abst ctx locate {context}` to locate your configs, leave context empty if you want to locate
  default

### Context commands

* `abst ctx list` to list contexts
* `abst ctx upgrade <context-name>` to upgrade context you can use `--all` flag to upgrade all contexts
* `abst ctx locate <context-name>` to get a full path of context
* `abst ctx share <context-name>` to copy context contents into clipboard and display it, you can use `--raw` to just
  get json
* `abst ctx paste <context-name>` to paste contents into context file provided from name

### Session commands

* `abst ssh` facilitates selecting an instance to connect to. The optional `port` argument can be specified partially; a
  connection is established if only one match is found. Use `-n <context-name>` to filter a connection, where the name
  can be a partial match. `abst` employs the `in` operator for searching and proceeds with SSH if a single matching
  instance exists.

### Parallel execution

If you are more demanding and need to have connection to your SSH Tunnels ready at all times
you can use parallel executed Bastions that currently work for full-auto forwarded setting

Change local port in the setting to port that is unique to other configs, and it will be running on
all the added ports
Until you kill the `abst` command, it will automatically remove all generated Bastion sessions by
this program

* `abst parallel add {context}` will add context from your `context folder` to stack that will be
  executed
* `abst parallel remove {context}` will remove context from your `context folder` to stack that
  will be executed
* `abst parallel run {context}` will run all the stacked contexts
* `abst parallel display` will display current stacked contexts
* `abst parallel list` will list all sets with contexts

### Helm registry commands

* `abst helm login` will log you in with credentials set in config.json, you set these credentials
  when running this command first time. Edit with flag --edit 1-n number is the index of credential
  in list
* `abst helm push <chart-name>` will push to specified remote branch, if more credentials preset it
  will let you pick which one to use

### Kubectl commands

* `abst pod ssh <part of name>` will ssh into pod with similar name, if multiple found it will display select
* `abst cp secret secret_namespace target_namespace source_namespace(optional)` this will copy
  secret to target namespace, without providing source namespace it will use current as a source

<hr>
Did I made your life less painful ? 
<br>
<br>
Support my coffee addiction ;)
<br>
<a href="https://www.buymeacoffee.com/jiriotoupal" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy me a Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>
