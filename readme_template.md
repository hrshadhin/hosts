[![latest release](https://img.shields.io/github/release/hrshadhin/hosts.svg)](https://github.com/hrshadhin/hosts/releases)
[![license](https://img.shields.io/badge/License-DBAD-brightgreen.svg)](https://github.com/hrshadhin/hosts/blob/master/LICENSE)
[![repo size](https://img.shields.io/github/repo-size/hrshadhin/hosts.svg)](https://github.com/hrshadhin/hosts)
[![Build Status](https://img.shields.io/github/workflow/status/hrshadhin/hosts/CI/master)](https://github.com/hrshadhin/hosts/actions?query=workflow%3ACI+branch%3Amaster)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![commits since last release](https://img.shields.io/github/commits-since/hrshadhin/hosts/latest.svg)](https://github.com/hrshadhin/hosts/commits/master)
[![last commit](https://img.shields.io/github/last-commit/hrshadhin/hosts.svg)](https://github.com/hrshadhin/hosts/commits/master)
[![commit activity](https://img.shields.io/github/commit-activity/y/hrshadhin/hosts.svg)](https://github.com/hrshadhin/hosts/commits/master)

<p align="center">
    <img src="https://raw.githubusercontent.com/hrshadhin/hosts/master/.github/logo.png">
</p>

**Take Note!**

* With the exception of issues and PRs regarding changes to 
  `hosts/sources/hrshadhin/hosts`, all other issues regarding the content of 
  the produced hosts files should be made with the appropriate data source 
  that contributed the content in question. The contact information for all 
  of the data sources can be found in the `hosts/sources/` directory.
----

# Unified hosts file

This repository consolidates several reputable `hosts` files, and merges them
into a unified hosts file with duplicates removed.

* Last updated: **@GEN_DATE@**.
* Here's the [raw hosts file](https://raw.githubusercontent.com/hrshadhin/hosts/master/hosts) containing @NUM_ENTRIES@ entries.
* This project is heavily inspired by [StevenBlack/hosts](https://github.com/StevenBlack/hosts/) project.

## Sources of hosts data unified in this variant

Updated `hosts` files from the following locations are always unified and
included:

Host file source | Description | Home page | Raw hosts | Update frequency | License | Issues
-----------------|-------------|:---------:|:---------:|:----------------:|:-------:|:------:
@SOURCEROWS@


## Generate your own unified hosts file

To generate your own amalgamated hosts files you will need Python 3.5 or later.

First, install the dependencies with:

```sh
python3 -m venv venv
source venv/bin/activate
pip install --user -r requirements.txt
```

### Common steps regardless of your development environment

To **run unit tests**, in the top-level directory, run:

```sh
python test_helpers.py
```

The `update_hosts_file.py` script will generate a unified hosts file based 
on the sources in the
local `sources/` subfolder.  The script will auto detect whether it should 
fetch updated versions  (from locations defined by the `info.json` text file 
in each source's folder). Otherwise, it will use the `hosts` file that's 
already there.

```sh
python update_hosts_file.py [--ip nnn.nnn.nnn.nnn] [--minimise]
```

#### Command line options

`--help`, or `-h`: display help.

`--ip nnn.nnn.nnn.nnn`, or `-i nnn.nnn.nnn.nnn`: the IP address to use as the
target.  Default is `0.0.0.0`.

`--empty-target-ip`, or `-e`: `false` (default) or `true`, omit IP part from
host rule. i.e: `example.com` instead of `0.0.0.0 example.com`

`--skip-static-hosts`, or `-s`: `false` (default) or `true`, omit the standard
section at the top, containing lines like `127.0.0.1 localhost`.  This is
useful for configuring proximate DNS services on the local network.

`--no-update`, or `-n`: skip fetching updates from hosts data sources.

`--output-directory <subfolder>`, or `-d <subfolder>`: place the generated 
source file in a subfolder.  If the subfolder does not exist, it will be created.

`--output-file <file_name>`, or `-o <file_name>`: named unified generated 
hosts file as given name, instead of `hosts`.

`--no-update-readme`, or `-nr`: `false` (default) or `true`, skip updating 
readme.md file. This is useful if you are generating host files with 
additional whitelists or blacklists and want to keep your local checkout of 
this repo unmodified.

`--minimise`, or `-m`: `false` (default) or `true`, *Compress* the hosts file
ignoring non-necessary lines (empty lines and comments). Reducing the 
number of lines of the hosts file improves the performances.

`--blacklist <black_list_file>`, or `-x <black_list_file>`: Append the given blacklist file in hosts format to the generated 
hosts file.

`--whitelist <white_list_file>`, or `-w <white_list_file>`: Use the given whitelist file to remove hosts from the generated 
hosts file.

## How do I control which sources are unified?

Add one or more *additional* sources, each in a subfolder of the `sources/`
folder, and specify the `url` key in its `info.json` file.

Create an *optional* `blacklist` file. The contents of this file (containing a
listing of additional domains in `hosts` file format) are appended to the
unified hosts file during the update process. A sample `blacklist` is
included, and may be modified as you need.

* NOTE: The `blacklist` is not tracked by git, so any changes you make won't
be overridden when you `git pull` this repo from `origin` in the future.

### How do I include my own custom domain mappings?

If you have custom hosts records, place them in file `custom_hosts`. The 
contents of this file are prepended to the unified hosts file during the update
process. if you pass `-empty-target-ip` or `-e` flag then contents of this file
will not added to the unified hosts file.

The `custom_hosts` file is not tracked by git, so any changes you make won't be
overridden when you `git pull` this repo from `origin` in the future.

### How do I prevent domains from being included?

The domains you list in the `whitelist` file are excluded from the final hosts
file.

The `whitelist` uses partial matching.  Therefore if you whitelist
`google-analytics.com`, that domain and all its subdomains won't be merged
into the final hosts file.

The `whitelist` is not tracked by git, so any changes you make won't be
overridden when you `git pull` this repo from `origin` in the future.

## How can I contribute hosts records?

If you discover sketchy domains you feel should be included here, here are some ways to contribute them.

### Option 1: contact one of the hosts sources

The best way to get new domains included is to submit an issue to any of 
the data providers whose home pages are [listed here](https://github.com/hrshadhin/hosts#sources-of-hosts-data-unified-in-this-variant). This is best because once you submit new domains, they will be curated and updated by the dedicated folks who maintain these sources.

### Option 2: Fork this repository, add your domains to H.R. Shadhin's personal data file, and submit a pull request

Fork this repo and add your links to [sources/hrshadhin/hosts](https://github.com/hrshadhin/hosts/blob/master/sources/hrshadhin/hosts).

Then, submit a pull request.

### Option 3: create your own hosts list as a repo on GitHub

If you're able to curate your own collection of sketchy domains, then curate your own hosts list.  Then signal the existence of your repo as [a new issue](https://github.com/hrshadhin/hosts/issues) and we may include your new repo into the collection of sources we pull whenever we create new versions.

## What is a hosts file?

A hosts file, named `hosts` (with no file extension), is a plain-text file
used by all operating systems to map hostnames to IP addresses.

In most operating systems, the `hosts` file is preferential to `DNS`.
Therefore if a domain name is resolved by the `hosts` file, the request never
leaves your computer.

Having a smart `hosts` file goes a long way towards blocking malware, adware,
and other irritants.

For example, to nullify requests to some doubleclick.net servers, adding these
lines to your hosts file will do it:

```text
# block doubleClick's servers
0.0.0.0 ad.ae.doubleclick.net
0.0.0.0 ad.ar.doubleclick.net
# etc...
```

## Location of your hosts file

To modify your current `hosts` file, look for it in the following places and modify it with a text
editor.

**GNU/Linux, macOS (until 10.14.x macOS Mojave), iOS, Android**: `/etc/hosts` 
file.

**macOS Catalina:** `/private/etc/hosts` file.

**Windows**: `%SystemRoot%\system32\drivers\etc\hosts` file.

## Reloading hosts file

Your operating system will cache DNS lookups. You can either reboot or run the following commands to
manually flush your DNS cache once the new hosts file is in place.

### GNU/Linux

Open a Terminal and run with root privileges:

**Debian/Ubuntu** `sudo service network-manager restart`

**Linux Mint** `sudo /etc/init.d/dns-clean start`

**GNU/Linux with systemd**: `sudo systemctl restart network.service`

**Fedora Linux**: `sudo systemctl restart NetworkManager.service`

**Arch Linux/Manjaro with Network Manager**: `sudo systemctl restart NetworkManager.service`

**Arch Linux/Manjaro with Wicd**: `sudo systemctl restart wicd.service`

**RHEL/Centos**: `sudo /etc/init.d/network restart`

**FreeBSD**: `sudo service nscd restart`

To enable the `nscd` daemon initially, it is recommended that you run the following commands:

```sh
sudo sysrc nscd_enable="YES"
sudo service nscd start
```

Then modify the `hosts` line in your `/etc/nsswitch.conf` file to the following:

```text
hosts: cache files dns
```

**Others**: Consult [this Wikipedia article](https://en.wikipedia.org/wiki/Hosts_%28file%29#Location_in_the_file_system).

### macOS

Open a Terminal and run:

```sh
sudo dscacheutil -flushcache;sudo killall -HUP mDNSResponder
```

## Goals of this unified hosts file

The goals of this repo are to:

1. automatically combine high-quality lists of hosts to block ads, malware, 
   spam, phishing, tracking sites.
2. by block sites via DNS actually we are reducing our bandwidth usage.
3. keep internet browsing happy by blocking those evil sites.


## Why this project exists!?

Have a similar project named [StevenBlack/hosts](https://github.com/StevenBlack/hosts/). 
So, why this project exist?

The reasons for existence of this repo are to:
1. we want custom formatted `hosts` file for our DNS proxy server [Blocky](https://github.com/0xERR0R/blocky)
2. also we want standard `hosts` file for other devices.
3. we want to manage more curated `sources` to collect hosts

## License
DON'T BE A DICK PUBLIC LICENSE
