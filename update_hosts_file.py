#!/usr/bin/env python3

# This Python script will combine all the host files from sources directory
# into one, unique host file to keep internet browsing happy by blocking
# those evil hosts.
import os
import sys

from helpers import (
    create_initial_file,
    ensure_output_path,
    get_defaults,
    load_exclusion_regexes,
    load_white_list,
    parse_args,
    update_all_sources,
    update_readme,
    write_final_file,
    write_opening_header,
)

# Detecting Python 3
PY3 = sys.version_info >= (3, 0)
if not PY3:
    raise Exception("We do not support Python 2 anymore.")


try:
    import requests  # noqa: F401
except ImportError:
    raise ImportError("The Requests library (https://docs.python-requests.org/en/latest/) " "is now required.")

# Settings
settings = {}


def main():
    options = parse_args()
    options["freshen"] = not options["no_update"]

    global settings
    settings = get_defaults()
    settings.update(options)

    settings["output_path"] = ensure_output_path(settings.get("output_directory", ""))
    output_file_name = settings["output_file"] if settings["output_file"] != "" else settings["host_file_name"]
    settings["output_file"] = output_file_name

    is_update_sources = settings["freshen"]
    if is_update_sources:
        update_all_sources(settings["source_path"], settings["source_info_file_name"], settings["host_file_name"])

    load_exclusion_regexes(settings["common_exclusions"], settings["exclusion_pattern"], settings["exclusion_regexes"])
    load_white_list(settings)

    merge_file = create_initial_file(settings)
    output_file = os.path.join(settings["output_path"], output_file_name)
    final_file = open(output_file, "w+b")
    write_final_file(merge_file, final_file, settings)
    write_opening_header(final_file, settings)
    final_file.close()

    if not settings["no_update_readme"]:
        update_readme(settings)

    print(
        f"Success! The hosts file has been saved in folder {settings['output_path']}\n"
        f"It contains {settings['number_of_rules']:,} unique entries."
    )


if __name__ == "__main__":
    main()
