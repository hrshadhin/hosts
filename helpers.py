# These helper functions are copied from Steven Black github repo(hosts).
# https://github.com/StevenBlack/hosts
# License: MIT

import argparse
import fnmatch
import json
import os
import platform
import re
import socket
import sys
import tempfile
import time
from glob import glob
from os.path import exists
from string import Template
from typing import Optional, Tuple

import requests

BASEDIR_PATH = os.path.dirname(os.path.realpath(__file__))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Creates a unified hosts file from hosts stored in the sources sub-folders."
    )
    parser.add_argument(
        "--ip",
        "-i",
        dest="target_ip",
        default="0.0.0.0",
        help="Target IP address. Default is 0.0.0.0.",
    )
    parser.add_argument(
        "--empty-target-ip",
        "-e",
        dest="empty_target_ip",
        action="store_true",
        default=False,
        help="Remove target IP. keep only host name.",
    )
    parser.add_argument(
        "--skip-static-hosts",
        "-s",
        dest="skip_static_hosts",
        default=False,
        action="store_true",
        help="Skip static localhost entries in the final hosts file.",
    )
    parser.add_argument(
        "--no-update",
        "-n",
        dest="no_update",
        default=False,
        action="store_true",
        help="Don't update from host data sources.",
    )
    parser.add_argument(
        "--no-update-readme",
        "-nr",
        dest="no_update_readme",
        default=False,
        action="store_true",
        help="Skip update readme file",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        dest="output_file",
        default="",
        help="Output file name for generated hosts file.",
    )
    parser.add_argument(
        "--output-directory",
        "-d",
        dest="output_directory",
        default="",
        help="Output sub folder/directory name for generated hosts file.",
    )
    parser.add_argument(
        "--minimise",
        "-m",
        dest="minimise",
        default=False,
        action="store_true",
        help="Minimise the hosts file ignoring non-necessary lines (empty lines and comments).",
    )
    parser.add_argument(
        "--whitelist",
        "-w",
        dest="white_list_file",
        default=os.path.join(BASEDIR_PATH, "white_list"),
        help="Whitelist file to use while generating hosts files.",
    )
    parser.add_argument(
        "--blacklist",
        "-x",
        dest="black_list_file",
        default=os.path.join(BASEDIR_PATH, "black_list"),
        help="Blacklist file to use while generating hosts files.",
    )

    return vars(parser.parse_args())


def get_defaults():
    """
    Helper method for getting the default settings.

    Returns
    -------
    settings : dict
        A dictionary of the default settings when updating host information.
    """

    return {
        "number_of_rules": 0,
        "host_file_name": "hosts",
        "target_ip": "0.0.0.0",
        "empty_target_ip": False,
        "freshen": True,
        "skip_static_hosts": False,
        "minimise": False,
        "source_path": os.path.join(BASEDIR_PATH, "sources"),
        "source_info_file_name": "info.json",
        "sources_data": [],
        "exclusions": [],
        "exclusion_regexes": [],
        "exclusion_pattern": r"([a-zA-Z\d-]+\.){0,}",
        "common_exclusions": [],
        "black_list_file": os.path.join(BASEDIR_PATH, "black_list"),
        "white_list_file": os.path.join(BASEDIR_PATH, "white_list"),
        "custom_host_file": os.path.join(BASEDIR_PATH, "custom_hosts"),
        "readme_file": "readme.md",
        "readme_template": os.path.join(BASEDIR_PATH, "readme_template.md"),
    }


def update_all_sources(source_path, info_file_name, host_filename):
    """
    Update all host files, regardless of folder depth.

    Parameters
    ----------
    source_path : str
        directory name that contains  all hosts sources
    info_file_name : str
        The name of the filename where information regarding updating
        sources for a particular URL is stored. This filename is assumed
        to be the same for all sources.
    host_filename : str
        The name of the file in which the updated source information
        is stored for a particular URL. This filename is assumed to be
        the same for all sources.
    """

    all_sources = recursive_glob(source_path, info_file_name)

    for source in all_sources:
        info_file = open(source, "r", encoding="UTF-8")
        source_info = json.load(info_file)
        info_file.close()

        file_url = source_info["url"]
        file_size = source_info["file_size"]
        source_name = source_info["name"]
        hosts_file_path = os.path.join(os.path.dirname(source), host_filename)
        file_exists = exists(hosts_file_path)

        print(f"Checking updates for source {source_name}")
        try:
            if not file_exists or is_remote_file_changed(file_size, file_url):
                print(f"Updating source {source_name}")
                updated_file, new_file_size = get_file_by_url(file_url)
                if updated_file is not None:
                    # get rid of carriage-return symbols
                    updated_file = updated_file.replace("\r", "")

                    hosts_file = open(hosts_file_path, "wb")
                    write_data(hosts_file, updated_file)
                    hosts_file.close()

                    source_info["file_size"] = int(new_file_size)
                    info_file = open(source, "wb")
                    write_data(info_file, json.dumps(source_info, indent=4))
                    info_file.close()
        except Exception as e:
            print(f"Error in updating source {source_name}. Error: {str(e)}")


def sort_sources(sources):
    """
    Sorts the sources.
    The idea is that all H.R. Shadhin's list, file or entries
    get on top and the rest sorted alphabetically.

    Parameters
    ----------
    sources: list
        The sources to sort.
    """

    result = sorted(sources.copy(), key=lambda x: x.lower().replace("-", "").replace("_", "").replace(" ", ""))

    # H.R. Shadhin's repositories/files/lists should be on top!
    positions = [x for x, y in enumerate(result) if "hrshadhin" in y.lower()]

    for index in positions:
        result.insert(0, result.pop(index))

    return result


def recursive_glob(stem, file_pattern):
    """
    Recursively match files in a directory according to a pattern.

    Parameters
    ----------
    stem : str
        The directory in which to recurse
    file_pattern : str
        The filename regex pattern to which to match.

    Returns
    -------
    matches_list : list
        A list of filenames in the directory that match the file pattern.
    """

    if sys.version_info >= (3, 5):
        return glob(stem + "/**/" + file_pattern, recursive=True)
    else:
        matches = []
        for root, dirnames, filenames in os.walk(stem):
            for filename in fnmatch.filter(filenames, file_pattern):
                matches.append(os.path.join(root, filename))
    return matches


def is_remote_file_changed(cur_file_size, url):
    """
    Retrieve the meta info of the hosts file at the URL, then check with
    existing file size

    Parameters are passed to the requests.get() function.

    Parameters
    ----------
    cur_file_size : int
        Current file size in bytes
    url : str or bytes
        URL for the new Request object.

    Returns
    -------
    is_changed : bool
        Returns True or False based on conditions. Returns False if the
        request attempted is unsuccessful.
    """

    try:
        req = requests.head(url=url)
    except requests.exceptions.RequestException:
        print("Error retrieving meta data from {}".format(url))
        return False
    if req.status_code == 404:
        print("404: {}".format(url))
        return False

    remote_file_size = int(req.headers.get("Content-Length", "0"))
    return remote_file_size > cur_file_size


def get_file_by_url(url, params=None, **kwargs):
    """
    Retrieve the contents of the hosts file at the URL, then pass it through
    domain_to_idna().

    Parameters are passed to the requests.get() function.

    Parameters
    ----------
    url : str or bytes
        URL for the new Request object.
    params :
        Dictionary, list of tuples or bytes to send in the query string for
        the Request.
    kwargs :
        Optional arguments that request takes.

    Returns
    -------
    url_data : str or None
        The data retrieved at that URL from the file. Returns None if the
        attempted retrieval is unsuccessful.
    content_size: int
        size of retrieved data in bytes
    """

    try:
        req = requests.get(url=url, params=params, **kwargs)
    except requests.exceptions.RequestException:
        print("Error retrieving data from {}".format(url))
        return None, 0

    if req.status_code == 404:
        print("404: {}".format(url))
        return None, 0

    req.encoding = req.apparent_encoding
    res_text = "\n".join([domain_to_idna(line.strip()) for line in req.text.split("\n")])
    return res_text, req.headers.get("Content-Length", "0")


def determine_separator(line):
    """
    Identify separator from line text

    :param line: str
    :return: str
    """

    tabs = "\t"
    space = " "

    tabs_position, space_position = (line.find(tabs), line.find(space))

    if tabs_position > -1 and space_position > -1:
        if space_position < tabs_position:
            separator = space
        else:
            separator = tabs
    elif not tabs_position == -1:
        separator = tabs
    elif not space_position == -1:
        separator = space
    else:
        separator = ""

    return separator


def domain_to_idna(line):
    """
    Encode a domain that is present into a line into `idna`. This way we
    avoid most encoding issues.

    Parameters
    ----------
    line : str
        The line we have to encode/decode.

    Returns
    -------
    line : str
        The line in a converted format.

    Notes
    -----
    - This function encodes only the domain to `idna` format because in
        most cases, the encoding issue is due to a domain which looks like
        `b'\xc9\xa2oogle.com'.decode('idna')`.
    - About the splitting:
        We split because we only want to encode the domain and not the full
        line, which may cause some issues. Keep in mind that we split, but we
        still concatenate once we encoded the domain.

        - The following split the prefix `0.0.0.0` or `127.0.0.1` of a line.
        - The following also split the trailing comment of a given line.
    """

    if not line.startswith("#"):
        separator = determine_separator(line)

        if separator:
            splited_line = line.split(separator)
            try:
                index = 1
                while index < len(splited_line):
                    if splited_line[index]:
                        break
                    index += 1

                if "#" in splited_line[index]:
                    index_comment = splited_line[index].find("#")

                    if index_comment > -1:
                        comment = splited_line[index][index_comment:]

                        splited_line[index] = (
                            splited_line[index].split(comment)[0].encode("IDNA").decode("UTF-8") + comment
                        )

                splited_line[index] = splited_line[index].encode("IDNA").decode("UTF-8")
            except IndexError:
                pass
            return separator.join(splited_line)
        return line.encode("IDNA").decode("UTF-8")
    return line.encode("UTF-8").decode("UTF-8")


def write_data(f, data):
    """
    Write data to a file object.

    Parameters
    ----------
    f : file
        The file object at which to write the data.
    data : str
        The data to write to the file.
    """

    f.write(bytes(data, "UTF-8"))


def load_exclusion_regexes(common_exclusions, pattern, regexes):
    """
    get the exclusion regex list

    This function checks whether need to exclude particular domains,
    and if so, excludes them.

    Parameters
    ----------
    common_exclusions : list
        A list of common domains that are excluded from being blocked. One
        example is Hulu. This setting is set directly in the script and cannot
        be overwritten by the user.
    pattern : str
        The exclusion pattern with which to create the domain regex.
    regexes : list
        The list of regex patterns used to exclude domains.

    Returns
    -------
    regexes : list
        List of regex patterns from domains which need to exclude.
    """

    for domain in common_exclusions:
        regex = re.compile(pattern + domain)
        regexes.append(regex)

    return regexes


def create_initial_file(settings):
    """
    Initialize the file in which we merge all host files for later pruning.
    """

    merge_file = tempfile.NamedTemporaryFile()

    # spin the sources for the base file
    for source in recursive_glob(settings["source_path"], settings["host_file_name"]):

        start = "# Start {}\n\n".format(os.path.basename(os.path.dirname(source)))
        end = "\n# End {}\n\n".format(os.path.basename(os.path.dirname(source)))

        with open(source, "r", encoding="UTF-8") as curFile:
            write_data(merge_file, start + curFile.read() + end)

    if os.path.isfile(settings["black_list_file"]):
        with open(settings["black_list_file"], "r") as curFile:
            write_data(merge_file, curFile.read())

    return merge_file


def ensure_output_path(path):
    """
    Check out put folder exists or create it
    :param path: str
    :return:
    """
    output_path = os.path.join(BASEDIR_PATH, path) if len(path) > 0 else BASEDIR_PATH

    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)

    return output_path


def load_white_list(settings):
    """
    Read while_list file and add host to exclusion list
    :param settings: dict
    :return: dict
    """
    if os.path.isfile(settings["white_list_file"]):
        with open(settings["white_list_file"], "r") as ins:
            for line in ins:
                line = line.strip(" \t\n\r")
                if line and not line.startswith("#"):
                    settings["exclusions"].append(line)


def write_final_file(temp_file, final_file, settings):
    """
    Write final hosts file. By pruning these things:
        - removing non-necessary lines (empty lines and comments)
        - remove duplicates and remove hosts that we are excluding
        - write slim file by removing target ip if needed

    Parameters
    ----------
    temp_file: file
    final_file: file
    settings: dict

    Returns
    -------
    final_file: fil
    """

    number_of_rules = settings["number_of_rules"]
    minimise = settings["minimise"]
    target_ip = "" if settings["empty_target_ip"] else settings["target_ip"]

    hostnames = {
        "localhost",
        "localhost.localdomain",
        "local",
        "broadcasthost",
    }

    temp_file.seek(0)  # reset file pointer

    for line in temp_file.readlines():
        write_line = True

        # Explicit encoding
        line = line.decode("UTF-8")

        # replace tabs with space
        line = line.replace("\t+", " ")

        # see gh-271: trim trailing whitespace, periods
        line = line.rstrip(" .")

        # Testing the first character doesn't require startswith
        if not minimise and (line[0] == "#" or re.match(r"^\s*$", line[0])):
            write_data(final_file, line)
            continue

        if "::1" in line:
            continue

        # strip comments
        stripped_rule = strip_rule(line, remove_comments=minimise)
        if not stripped_rule or matches_exclusions(stripped_rule, settings["exclusion_regexes"]):
            continue

        # Issue #1628
        if "@" in stripped_rule:
            continue

        # Normalize rule
        hostname, normalized_rule = normalize_rule(stripped_rule, target_ip, keep_domain_comments=minimise)

        for exclude in settings["exclusions"]:
            if re.search(r"(^|[\s\.])" + re.escape(exclude) + r"\s", line):
                write_line = False
                break

        if normalized_rule and (hostname not in hostnames) and write_line:
            write_data(final_file, normalized_rule)
            hostnames.add(hostname)
            number_of_rules += 1

    settings["number_of_rules"] = number_of_rules
    temp_file.close()


def strip_rule(line, remove_comments=False):
    """
    Sanitize a rule string provided before writing it to the output hosts file.

    Parameters
    ----------
    line : str
        The rule provided for sanitation.
    remove_comments: bool
        Remove comments from rule string
    Returns
    -------
    sanitized_line : str
        The sanitized rule.
    """
    if remove_comments:
        line = line[: line.find("#")].strip()

    return line


def matches_exclusions(stripped_rule, exclusion_regexes):
    """
    Check whether a rule matches an exclusion rule we already provided.

    If this function returns True, that means this rule should be excluded
    from the final hosts file.

    Parameters
    ----------
    stripped_rule : str
        The rule that we are checking.
    exclusion_regexes : list
        The list of regex patterns used to exclude domains.

    Returns
    -------
    matches_exclusion : bool
        Whether or not the rule string matches a provided exclusion.
    """

    try:
        stripped_domain = stripped_rule.split()[1]
    except IndexError:
        # Example: 'example.org' instead of '0.0.0.0 example.org'
        stripped_domain = stripped_rule

    for exclusionRegex in exclusion_regexes:
        if exclusionRegex.search(stripped_domain):
            return True

    return False


def normalize_rule(rule, target_ip, keep_domain_comments):
    """
    Standardize and format the rule string provided.

    Parameters
    ----------
    rule : str
        The rule whose spelling and spacing we are standardizing.
    target_ip : str
        The target IP address for the rule.
    keep_domain_comments : bool
        Whether or not to keep comments regarding these domains in
        the normalized rule.
    Returns
    -------
    normalized_rule : tuple
        A tuple of the hostname and the rule string with spelling
        and spacing reformatted.
    """

    def normalize_response(extracted_hostname: str, extracted_suffix: Optional[str]) -> Tuple[str, str]:
        """
        Normalizes the responses after the provision of the extracted
        hostname and suffix - if exist.

        Parameters
        ----------
        extracted_hostname: str
            The extracted hostname to work with.
        extracted_suffix: str
            The extracted suffix to with.

        Returns
        -------
        normalized_response: tuple
            A tuple of the hostname and the rule string with spelling
            and spacing reformatted.
        """
        if len(target_ip) > 0:
            final_rule = f"{target_ip} {extracted_hostname}"

            if keep_domain_comments and extracted_suffix:
                final_rule += f" #{extracted_suffix}"

            final_rule += "\n"
        else:
            final_rule = f"{extracted_hostname}\n"

        return extracted_hostname, final_rule

    """
    first try: IP followed by domain
    """
    regex = r"^\s*(\d{1,3}\.){3}\d{1,3}\s+([\w\.-]+[a-zA-Z])(.*)"
    result = re.search(regex, rule)

    if result:
        hostname, suffix = result.group(2, 3)

        # Explicitly lowercase and trim the hostname.
        hostname = hostname.lower().strip()

        return normalize_response(hostname, suffix)

    """
    next try: IP address followed by host IP address
    """
    regex = r"^\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+(\d{1,3}\.\d{1," r"3}\.\d{1,3}\.\d{1,3})\s*(.*)"
    result = re.search(regex, rule)

    if result:
        ip_host, suffix = result.group(2, 3)
        # Explicitly trim the ip host.
        ip_host = ip_host.strip()

        return normalize_response(ip_host, suffix)

    """
    next try: Keep RAW domain.
    """
    regex = r"^\s*([\w\.-]+[a-zA-Z])(.*)"
    result = re.search(regex, rule)

    if result:
        hostname, suffix = result.group(1, 2)

        # Explicitly lowercase and trim the hostname.
        hostname = hostname.lower().strip()

        return normalize_response(hostname, suffix)

    """
    finally, if we get here, just belch to screen
    """
    print("==>%s<==" % rule)
    return None, None


def write_opening_header(final_file, settings):
    """
    Write the header information into the newly-created hosts file.

    Parameters
    ----------
    final_file : file
        The file object that points to the newly-created hosts file.
    settings : dict
        Dictionary providing additional parameters for populating the header
        information.
    """

    final_file.seek(0)  # Reset file pointer.
    file_contents = final_file.read()  # Save content.

    final_file.seek(0)  # Write at the top.

    write_data(final_file, "# Title: hrshadhin/hosts\n#\n")

    write_data(
        final_file,
        "# This hosts file is a merged collection of hosts from reputable " "sources,\n",
    )
    write_data(final_file, "# with a dash of crowd sourcing via GitHub\n#\n")
    write_data(
        final_file,
        f"# Date: {time.strftime('%d %B %Y %H:%M:%S (%Z)', time.gmtime())}\n",
    )

    write_data(
        final_file,
        ("# Number of unique domains: {:,}\n#\n".format(settings["number_of_rules"])),
    )

    file_path = settings.get("output_directory", "").replace("\\", "/")
    if len(file_path) > 0:
        file_path = f"{file_path}/"
    file_path = f"{file_path}{settings['output_file']}\n"

    write_data(
        final_file,
        f"# Fetch the latest version of this file: "
        f"https://raw.githubusercontent.com/hrshadhin/hosts/master/"
        f"{file_path}",
    )
    write_data(final_file, "# Project home page: https://github.com/hrshadhin/hosts\n")
    write_data(
        final_file,
        "# Project releases: https://github.com/hrshadhin/hosts/releases\n#",
    )
    write_data(
        final_file,
        " ===============================================================\n",
    )
    write_data(final_file, "\n")

    if not settings["skip_static_hosts"]:
        write_data(final_file, "127.0.0.1 localhost\n")
        write_data(final_file, "127.0.0.1 localhost.localdomain\n")
        write_data(final_file, "127.0.0.1 local\n")
        write_data(final_file, "255.255.255.255 broadcasthost\n")
        write_data(final_file, "::1 localhost\n")
        write_data(final_file, "::1 ip6-localhost\n")
        write_data(final_file, "::1 ip6-loopback\n")
        write_data(final_file, "fe80::1%lo0 localhost\n")
        write_data(final_file, "ff00::0 ip6-localnet\n")
        write_data(final_file, "ff00::0 ip6-mcastprefix\n")
        write_data(final_file, "ff02::1 ip6-allnodes\n")
        write_data(final_file, "ff02::2 ip6-allrouters\n")
        write_data(final_file, "ff02::3 ip6-allhosts\n")
        write_data(final_file, "0.0.0.0 0.0.0.0\n")

        if platform.system() == "Linux":
            write_data(final_file, "127.0.1.1 " + socket.gethostname() + "\n")
            write_data(final_file, "127.0.0.53 " + socket.gethostname() + "\n")

        write_data(final_file, "\n")

    if not settings["empty_target_ip"]:
        preamble = settings.get("custom_host_file", "")
        if os.path.isfile(preamble):
            with open(preamble, "r") as f:
                write_data(final_file, f.read())
                write_data(final_file, "\n")

    final_file.write(file_contents)


def load_sources_data(sources_data, **sources_params):
    """
    Load the sources data and information for each source.

    Parameters
    ----------
    sources_data : list
        The list of sources data that we are to update.
    sources_params : kwargs
        Dictionary providing additional parameters for updating the
        sources data. Currently, those fields are:

        1) data_path
        2) info_file_name

    Returns
    -------
    sources_data : list
        The original source data list with new source data appended.
    """

    for source in sort_sources(recursive_glob(sources_params["data_path"], sources_params["info_file_name"])):
        update_file = open(source, "r", encoding="UTF-8")
        update_data = json.load(update_file)
        sources_data.append(update_data)
        update_file.close()

    return sources_data


def update_readme(settings):
    """
    Update readme files in this repo

    :param settings: dict
    :return:
    """
    sources_data = []
    sources_data = load_sources_data(
        sources_data,
        data_path=settings["source_path"],
        info_file_name=settings["source_info_file_name"],
    )

    row_defaults = {
        "name": "",
        "description": "",
        "home_url": "",
        "frequency": "",
        "url": "",
        "license": "",
        "issues": "",
    }

    t = Template(
        "${name} | ${description} |[link](${home_url})"
        " | [raw](${url}) | ${frequency} | ${license} | [issues](${issues})"
    )
    source_rows = ""
    for source in sources_data:
        this_row = {}
        this_row.update(row_defaults)
        this_row.update(source)
        source_rows += t.substitute(this_row) + "\n"

    with open(settings["readme_file"], "wt", encoding="utf-8", newline="\n") as out:
        with open(settings["readme_template"], encoding="utf-8", newline="\n") as rt_file:
            for line in rt_file.readlines():
                line = line.replace("@GEN_DATE@", time.strftime("%B %d %Y", time.gmtime()))
                line = line.replace("@NUM_ENTRIES@", "{:,}".format(settings["number_of_rules"]))
                line = line.replace("@SOURCEROWS@", source_rows)
                out.write(line)
