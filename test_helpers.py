#!/usr/bin/env python3

import os
import platform
import shutil
import sys
import tempfile
import unittest
import unittest.mock as mock
from io import BytesIO, StringIO

import requests

import helpers
from helpers import (
    domain_to_idna,
    get_defaults,
    get_file_by_url,
    is_remote_file_changed,
    normalize_rule,
    sort_sources,
    strip_rule,
    update_all_sources,
    write_data,
    write_opening_header,
    update_readme,
)


class Base(unittest.TestCase):
    @staticmethod
    def mock_property(name):
        return mock.patch(name, new_callable=mock.PropertyMock)

    @property
    def sep(self):
        if platform.system().lower() == "windows":
            return "\\"
        return os.sep

    def assert_called_once(self, mock_method):
        self.assertEqual(mock_method.call_count, 1)


class BaseStdout(Base):
    def setUp(self):
        sys.stdout = StringIO()

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = sys.__stdout__


class BaseMockDir(Base):
    @property
    def dir_count(self):
        return len(os.listdir(self.test_dir))

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)


# Project Settings
class TestGetDefaults(Base):
    def test_get_defaults(self):
        with self.mock_property("helpers.BASEDIR_PATH"):
            helpers.BASEDIR_PATH = "foobar"
            actual = get_defaults()
            expected = {
                "number_of_rules": 0,
                "host_file_name": "hosts",
                "target_ip": "0.0.0.0",
                "empty_target_ip": False,
                "freshen": True,
                "skip_static_hosts": False,
                "minimise": False,
                "source_path": "foobar" + self.sep + "sources",
                "source_info_file_name": "info.json",
                "sources_data": [],
                "exclusions": [],
                "exclusion_regexes": [],
                "exclusion_pattern": r"([a-zA-Z\d-]+\.){0,}",
                "common_exclusions": [],
                "black_list_file": "foobar" + self.sep + "black_list",
                "white_list_file": "foobar" + self.sep + "white_list",
                "custom_host_file": "foobar" + self.sep + "custom_hosts",
                "readme_file": "readme.md",
                "readme_template": "foobar" + self.sep + "readme_template.md",
            }
            self.assertDictEqual(actual, expected)


class TestUpdateAllSources(BaseStdout):
    def setUp(self):
        BaseStdout.setUp(self)
        self.source_name = "foo"
        self.source_path = "foobar/sources"
        self.source_info_filename = "info.json"
        self.host_filename = "hosts.txt"

    @mock.patch("builtins.open")
    @mock.patch("helpers.recursive_glob", return_value=[])
    def test_no_sources(self, _, mock_open):
        update_all_sources(self.source_path, self.source_info_filename, self.host_filename)
        mock_open.assert_not_called()

    @mock.patch("builtins.open", return_value=mock.Mock())
    @mock.patch("json.load", return_value={"name": "example", "url": "example.com", "file_size": 0})
    @mock.patch("helpers.recursive_glob", return_value=["foo"])
    @mock.patch("helpers.write_data", return_value=0)
    @mock.patch("helpers.get_file_by_url", return_value=("file_data", 10))
    def test_one_source(self, mock_get, mock_write, *_):
        update_all_sources(self.source_path, self.source_info_filename, self.host_filename)
        self.assertEqual(mock_write.call_count, 2)
        self.assert_called_once(mock_get)

        output = sys.stdout.getvalue()
        expected = "Updating source example"
        self.assertIn(expected, output)

    @mock.patch("builtins.open", return_value=mock.Mock())
    @mock.patch("json.load", return_value={"name": "example", "url": "example.com", "file_size": 0})
    @mock.patch("helpers.recursive_glob", return_value=["foo"])
    @mock.patch("helpers.write_data", return_value=0)
    @mock.patch("helpers.get_file_by_url", return_value=Exception("fail"))
    def test_source_fail(self, mock_get, mock_write, *_):
        update_all_sources(self.source_path, self.source_info_filename, self.host_filename)
        mock_write.assert_not_called()
        self.assert_called_once(mock_get)

        output = sys.stdout.getvalue()
        expecteds = [
            "Checking updates for source example",
            "Error in updating source example",
        ]
        for expected in expecteds:
            self.assertIn(expected, output)

    @mock.patch("builtins.open", return_value=mock.Mock())
    @mock.patch(
        "json.load",
        side_effect=[
            {"name": "example", "url": "example.com", "file_size": 0},
            {"name": "example2", "url": "example2.com", "file_size": 0},
        ],
    )
    @mock.patch("helpers.recursive_glob", return_value=["foo", "bar"])
    @mock.patch("helpers.write_data", return_value=0)
    @mock.patch("helpers.get_file_by_url", side_effect=[Exception("fail"), ("file_data", 10)])
    def test_sources_fail_succeed(self, mock_get, mock_write, *_):
        update_all_sources(self.source_path, self.source_info_filename, self.host_filename)
        self.assertEqual(mock_write.call_count, 2)

        get_calls = [mock.call("example.com"), mock.call("example2.com")]
        mock_get.assert_has_calls(get_calls)

        output = sys.stdout.getvalue()
        expecteds = [
            "Updating source example",
            "Error in updating source example",
            "Updating source example2",
        ]
        for expected in expecteds:
            self.assertIn(expected, output)


class TestSortSources(Base):
    def test_sort_sources_simple(self):
        given = [
            "sbc.io",
            "example.com",
            "github.com",
        ]

        expected = ["example.com", "github.com", "sbc.io"]

        actual = sort_sources(given)

        self.assertEqual(actual, expected)

    def test_live_data(self):
        given = [
            "sources/KADhosts/info.json",
            "sources/someonewhocares.org/info.json",
            "sources/hrshadhin/info.json",
            "sources/adaway.org/info.json",
            "sources/URLHaus/info.json",
            "sources/UncheckyAds/info.json",
            "sources/add.2o7Net/info.json",
            "sources/mvps.org/info.json",
            "sources/add.Spam/info.json",
            "sources/add.Dead/info.json",
            "sources/malwaredomainlist.com/info.json",
            "sources/Badd-Boyz-Hosts/info.json",
            "sources/hostsVN/info.json",
            "sources/yoyo.org/info.json",
            "sources/add.Risk/info.json",
            "sources/tiuxo/info.json",
        ]

        expected = [
            "sources/hrshadhin/info.json",
            "sources/adaway.org/info.json",
            "sources/add.2o7Net/info.json",
            "sources/add.Dead/info.json",
            "sources/add.Risk/info.json",
            "sources/add.Spam/info.json",
            "sources/Badd-Boyz-Hosts/info.json",
            "sources/hostsVN/info.json",
            "sources/KADhosts/info.json",
            "sources/malwaredomainlist.com/info.json",
            "sources/mvps.org/info.json",
            "sources/someonewhocares.org/info.json",
            "sources/tiuxo/info.json",
            "sources/UncheckyAds/info.json",
            "sources/URLHaus/info.json",
            "sources/yoyo.org/info.json",
        ]

        actual = sort_sources(given)

        self.assertEqual(actual, expected)


class TestNormalizeRule(BaseStdout):
    def test_no_match(self):
        # Note: "Bare"- Domains are accepted. IP are excluded.
        for rule in [
            "128.0.0.1",
            "0.0.0 google",
            "0.1.2.3.4 foo/bar",
        ]:
            self.assertEqual(normalize_rule(rule, target_ip="0.0.0.0", keep_domain_comments=True), (None, None))

            output = sys.stdout.getvalue()
            sys.stdout = StringIO()

            expected = "==>" + rule + "<=="
            self.assertIn(expected, output)

    def test_no_comments(self):
        for target_ip in ("0.0.0.0", "127.0.0.1", "8.8.8.8"):
            rule = "127.0.0.1 1.google.com foo"
            expected = ("1.google.com", str(target_ip) + " 1.google.com\n")

            actual = normalize_rule(rule, target_ip=target_ip, keep_domain_comments=False)
            self.assertEqual(actual, expected)

            # Nothing gets printed if there's a match.
            output = sys.stdout.getvalue()
            self.assertEqual(output, "")

            sys.stdout = StringIO()

    def test_with_comments(self):
        for target_ip in ("0.0.0.0", "127.0.0.1", "8.8.8.8"):
            for comment in ("foo", "bar", "baz"):
                rule = "127.0.0.1 1.google.co.uk " + comment
                expected = ("1.google.co.uk", (str(target_ip) + " 1.google.co.uk # " + comment + "\n"))
                actual = normalize_rule(rule, target_ip=target_ip, keep_domain_comments=True)
                self.assertEqual(actual, expected)

                # Nothing gets printed if there's a match.
                output = sys.stdout.getvalue()
                self.assertEqual(output, "")

                sys.stdout = StringIO()

    def test_two_ips(self):
        for target_ip in ("0.0.0.0", "127.0.0.1", "8.8.8.8"):
            rule = "127.0.0.1 11.22.33.44 foo"
            expected = ("11.22.33.44", str(target_ip) + " 11.22.33.44\n")

            actual = normalize_rule(rule, target_ip=target_ip, keep_domain_comments=False)
            self.assertEqual(actual, expected)

            # Nothing gets printed if there's a match.
            output = sys.stdout.getvalue()
            self.assertEqual(output, "")

            sys.stdout = StringIO()

    def test_no_comment_raw(self):
        for rule in ("twitter.com", "google.com", "foo.bar.edu"):
            expected = (rule, "0.0.0.0 " + rule + "\n")

            actual = normalize_rule(rule, target_ip="0.0.0.0", keep_domain_comments=False)
            self.assertEqual(actual, expected)

            # Nothing gets printed if there's a match.
            output = sys.stdout.getvalue()
            self.assertEqual(output, "")

            sys.stdout = StringIO()

    def test_with_comments_raw(self):
        for target_ip in ("0.0.0.0", "127.0.0.1", "8.8.8.8"):
            for comment in ("foo", "bar", "baz"):
                rule = "1.google.co.uk " + comment
                expected = ("1.google.co.uk", f"{target_ip} 1.google.co.uk # {comment}\n")

                actual = normalize_rule(rule, target_ip=target_ip, keep_domain_comments=True)
                self.assertEqual(actual, expected)

                # Nothing gets printed if there's a match.
                output = sys.stdout.getvalue()
                self.assertEqual(output, "")

                sys.stdout = StringIO()

    def test_no_comment_only_hostname(self):
        for rule in ("t2222.com", "g22222.com", "f3ere.bar.edu"):
            expected = (rule, f"{rule}\n")
            actual = normalize_rule(rule, target_ip="", keep_domain_comments=False)
            self.assertEqual(actual, expected)

            # Nothing gets printed if there's a match.
            output = sys.stdout.getvalue()
            self.assertEqual(output, "")

            sys.stdout = StringIO()


class TestStripRule(Base):
    def test_strip_exactly_two(self):
        for line in [
            "0.0.0.0 twitter.com",
            "127.0.0.1 facebook.com",
            "8.8.8.8 google.com",
            "1.2.3.4 foo.bar.edu",
        ]:
            output = strip_rule(line)
            self.assertEqual(output, line)

    def test_strip_more_than_two(self):
        comment = " # comments here galore"

        for line in [
            "0.0.0.0 twitter.com",
            "127.0.0.1 facebook.com",
            "8.8.8.8 google.com",
            "1.2.3.4 foo.bar.edu",
        ]:
            output = strip_rule(line + comment)
            self.assertEqual(output, line + comment)

    def test_strip_raw(self):
        for line in [
            "twitter.com",
            "facebook.com",
            "google.com",
            "foo.bar.edu",
        ]:
            output = strip_rule(line)
            self.assertEqual(output, line)

    def test_strip_raw_with_comment(self):
        comment = " # comments here galore"

        for line in [
            "twitter.com",
            "facebook.com",
            "google.com",
            "foo.bar.edu",
        ]:
            output = strip_rule(f"{line}{comment} more text... {line}", remove_comments=True)
            self.assertEqual(output, line)


class DomainToIDNA(Base):
    def __init__(self, *args, **kwargs):
        super(DomainToIDNA, self).__init__(*args, **kwargs)

        self.domains = [b"\xc9\xa2oogle.com", b"www.huala\xc3\xb1e.cl"]
        self.expected_domains = ["xn--oogle-wmc.com", "www.xn--hualae-0wa.cl"]

    def test_empty_line(self):
        data = ["", "\r", "\n"]

        for empty in data:
            expected = empty

            actual = domain_to_idna(empty)
            self.assertEqual(actual, expected)

    def test_commented_line(self):
        data = "# Hello World"
        expected = data
        actual = domain_to_idna(data)

        self.assertEqual(actual, expected)

    def test_simple_line(self):
        # Test with a space as separator.
        for i in range(len(self.domains)):
            data = (b"0.0.0.0 " + self.domains[i]).decode("utf-8")
            expected = "0.0.0.0 " + self.expected_domains[i]

            actual = domain_to_idna(data)

            self.assertEqual(actual, expected)

        # Test with a tabulation as separator.
        for i in range(len(self.domains)):
            data = (b"0.0.0.0\t" + self.domains[i]).decode("utf-8")
            expected = "0.0.0.0\t" + self.expected_domains[i]

            actual = domain_to_idna(data)

            self.assertEqual(actual, expected)

    def test_multiple_space_as_separator(self):
        # Test with multiple space as separator.
        for i in range(len(self.domains)):
            data = (b"0.0.0.0      " + self.domains[i]).decode("utf-8")
            expected = "0.0.0.0      " + self.expected_domains[i]

            actual = domain_to_idna(data)

            self.assertEqual(actual, expected)

    def test_multiple_tabs_as_separator(self):
        # Test with multiple tabls as separator.
        for i in range(len(self.domains)):
            data = (b"0.0.0.0\t\t\t\t\t\t" + self.domains[i]).decode("utf-8")
            expected = "0.0.0.0\t\t\t\t\t\t" + self.expected_domains[i]

            actual = domain_to_idna(data)

            self.assertEqual(actual, expected)

    def test_line_with_comment_at_the_end(self):
        # Test with a space as separator.
        for i in range(len(self.domains)):
            data = (b"0.0.0.0 " + self.domains[i] + b" # Hello World").decode("utf-8")
            expected = "0.0.0.0 " + self.expected_domains[i] + " # Hello World"

            actual = domain_to_idna(data)

            self.assertEqual(actual, expected)

        # Test with a tabulation as separator.
        for i in range(len(self.domains)):
            data = (b"0.0.0.0\t" + self.domains[i] + b" # Hello World").decode("utf-8")
            expected = "0.0.0.0\t" + self.expected_domains[i] + " # Hello World"

            actual = domain_to_idna(data)

            self.assertEqual(actual, expected)

        # Test with tabulation as separator of domain and comment.
        for i in range(len(self.domains)):
            data = (b"0.0.0.0\t" + self.domains[i] + b"\t # Hello World").decode("utf-8")
            expected = "0.0.0.0\t" + self.expected_domains[i] + "\t # Hello World"

            actual = domain_to_idna(data)

            self.assertEqual(actual, expected)

        # Test with space as separator of domain and tabulation as separator
        # of comments.
        for i in range(len(self.domains)):
            data = (b"0.0.0.0 " + self.domains[i] + b"  \t # Hello World").decode("utf-8")
            expected = "0.0.0.0 " + self.expected_domains[i] + "  \t # Hello World"

            actual = domain_to_idna(data)

            self.assertEqual(actual, expected)

        # Test with multiple space as separator of domain and space and
        # tabulation as separator or comments.
        for i in range(len(self.domains)):
            data = (b"0.0.0.0     " + self.domains[i] + b" \t # Hello World").decode("utf-8")
            expected = "0.0.0.0     " + self.expected_domains[i] + " \t # Hello World"

            actual = domain_to_idna(data)

            self.assertEqual(actual, expected)

        # Test with multiple tabulations as separator of domain and space and
        # tabulation as separator or comments.
        for i, domain in enumerate(self.domains):
            data = (b"0.0.0.0\t\t\t" + domain + b" \t # Hello World").decode("utf-8")
            expected = "0.0.0.0\t\t\t" + self.expected_domains[i] + " \t # Hello World"

            actual = domain_to_idna(data)

            self.assertEqual(actual, expected)

    def test_line_without_prefix(self):
        for i in range(len(self.domains)):
            data = self.domains[i].decode("utf-8")
            expected = self.expected_domains[i]

            actual = domain_to_idna(data)

            self.assertEqual(actual, expected)


class IsFileChangedByUrl(BaseStdout):
    def test_file_changed(self):
        headers = {"Content-Length": 10}
        resp_obj = requests.Response()
        resp_obj.__setstate__({"headers": headers})

        with mock.patch("requests.head", return_value=resp_obj):
            is_changed = is_remote_file_changed(5, "www.test-url.com")

        self.assertTrue(is_changed)

    def test_file_not_changed(self):
        headers = {"Content-Length": 100}
        resp_obj = requests.Response()
        resp_obj.__setstate__({"headers": headers})

        with mock.patch("requests.head", return_value=resp_obj):
            is_changed = is_remote_file_changed(100, "www.test-url.com")

        self.assertFalse(is_changed)


class GetFileByUrl(BaseStdout):
    def test_basic(self):
        raw_resp_content = "hello, ".encode("ascii") + "world".encode("utf-8")
        resp_obj = requests.Response()
        resp_obj.__setstate__({"_content": raw_resp_content})

        expected = "hello, world"

        with mock.patch("requests.get", return_value=resp_obj):
            actual, content_size = get_file_by_url("www.test-url.com")

        self.assertEqual(expected, actual)

    def test_with_idna(self):
        raw_resp_content = b"www.huala\xc3\xb1e.cl"
        resp_obj = requests.Response()
        resp_obj.__setstate__({"_content": raw_resp_content})

        expected = "www.xn--hualae-0wa.cl"

        with mock.patch("requests.get", return_value=resp_obj):
            actual, content_size = get_file_by_url("www.test-url.com")

        self.assertEqual(expected, actual)

    def test_connect_unknown_domain(self):
        test_url = "http://doesnotexist.google.com"  # leads to exception: ConnectionError
        with mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError):
            return_value, content_size = get_file_by_url(test_url)
        self.assertIsNone(return_value)
        printed_output = sys.stdout.getvalue()
        self.assertEqual(printed_output, "Error retrieving data from {}\n".format(test_url))

    def test_invalid_url(self):
        test_url = "http://fe80::5054:ff:fe5a:fc0"  # leads to exception: InvalidURL
        with mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError):
            return_value, content_size = get_file_by_url(test_url)
        self.assertIsNone(return_value)
        printed_output = sys.stdout.getvalue()
        self.assertEqual(printed_output, "Error retrieving data from {}\n".format(test_url))


class TestWriteData(Base):
    def test_write_basic(self):
        f = BytesIO()

        data = "foo"
        write_data(f, data)

        expected = b"foo"
        actual = f.getvalue()

        self.assertEqual(actual, expected)

    def test_write_unicode(self):
        f = BytesIO()

        data = "foo"
        write_data(f, data)

        expected = b"foo"
        actual = f.getvalue()

        self.assertEqual(actual, expected)


class TestWriteOpeningHeader(BaseMockDir):
    def setUp(self):
        super(TestWriteOpeningHeader, self).setUp()
        self.final_file = BytesIO()

    def test_missing_keyword(self):
        kwargs = dict(empty_target_ip=False, output_file="hosts", number_of_rules=5, skip_static_hosts=False)

        for k in kwargs.keys():
            bad_kwargs = kwargs.copy()
            bad_kwargs.pop(k)

            self.assertRaises(KeyError, write_opening_header, self.final_file, bad_kwargs)

    def test_basic(self):
        kwargs = dict(empty_target_ip=False, output_file="hosts", number_of_rules=5, skip_static_hosts=True)

        write_opening_header(self.final_file, kwargs)

        contents = self.final_file.getvalue()
        contents = contents.decode("UTF-8")

        # Expected contents.
        for expected in (
            "# This hosts file is a merged collection",
            "# with a dash of crowd sourcing via GitHub",
            "# Number of unique domains: {count}".format(count=kwargs["number_of_rules"]),
            "Fetch the latest version of this file:",
            "Project home page: https://github.com/hrshadhin/hosts",
        ):
            self.assertIn(expected, contents)

        # Expected non-contents.
        for expected in (
            "# Extensions added to this file:",
            "127.0.0.1 localhost",
            "127.0.0.1 local",
            "127.0.0.53",
            "127.0.1.1",
        ):
            self.assertNotIn(expected, contents)

    def test_basic_include_static_hosts(self):
        kwargs = dict(empty_target_ip=True, output_file="hosts", number_of_rules=5, skip_static_hosts=False)

        with self.mock_property("platform.system") as obj:
            obj.return_value = "Windows"
            write_opening_header(self.final_file, kwargs)

        contents = self.final_file.getvalue()
        contents = contents.decode("UTF-8")

        # Expected contents.
        for expected in (
            "127.0.0.1 local",
            "127.0.0.1 localhost",
            "# This hosts file is a merged collection",
            "# with a dash of crowd sourcing via GitHub",
            "# Number of unique domains: {count}".format(count=kwargs["number_of_rules"]),
            "Fetch the latest version of this file:",
            "Project home page: https://github.com/hrshadhin/hosts",
        ):
            self.assertIn(expected, contents)

        # Expected non-contents.
        for expected in ("# Extensions added to this file:", "127.0.0.53", "127.0.1.1"):
            self.assertNotIn(expected, contents)

    def test_basic_include_static_hosts_linux(self):
        kwargs = dict(empty_target_ip=False, output_file="hosts", number_of_rules=5, skip_static_hosts=False)

        with self.mock_property("platform.system") as system:
            system.return_value = "Linux"

            with self.mock_property("socket.gethostname") as hostname:
                hostname.return_value = "hrs-hosts"
                write_opening_header(self.final_file, kwargs)

        contents = self.final_file.getvalue()
        contents = contents.decode("UTF-8")

        # Expected contents.
        for expected in (
            "127.0.1.1",
            "127.0.0.53",
            "hrs-hosts",
            "127.0.0.1 local",
            "127.0.0.1 localhost",
            "# This hosts file is a merged collection",
            "# with a dash of crowd sourcing via GitHub",
            "# Number of unique domains: {count}".format(count=kwargs["number_of_rules"]),
            "Fetch the latest version of this file:",
            "Project home page: https://github.com/hrshadhin/hosts",
        ):
            self.assertIn(expected, contents)

        # Expected non-contents.
        expected = "# Extensions added to this file:"
        self.assertNotIn(expected, contents)

    def test_preamble_copy(self):
        hosts_file = os.path.join(self.test_dir, "custom_hosts")

        with open(hosts_file, "w") as f:
            f.write("foobar-foobar-foo-bar-bar-foo")

        kwargs = dict(
            custom_host_file=hosts_file,
            empty_target_ip=False,
            output_file="hosts",
            number_of_rules=5,
            skip_static_hosts=True,
        )

        write_opening_header(self.final_file, kwargs)
        contents = self.final_file.getvalue()
        contents = contents.decode("UTF-8")

        # Expected contents.
        for expected in (
            "foobar-foobar-foo-bar-bar-foo",
            "# This hosts file is a merged collection",
            "# with a dash of crowd sourcing via GitHub",
            "# Number of unique domains: {count}".format(count=kwargs["number_of_rules"]),
            "Fetch the latest version of this file:",
            "Project home page: https://github.com/hrshadhin/hosts",
        ):
            self.assertIn(expected, contents)

        # Expected non-contents.
        for expected in (
            "# Extensions added to this file:",
            "127.0.0.1 localhost",
            "127.0.0.1 local",
            "127.0.0.53",
            "127.0.1.1",
        ):
            self.assertNotIn(expected, contents)

    def tearDown(self):
        super(TestWriteOpeningHeader, self).tearDown()
        self.final_file.close()


class TestUpdateReadme(BaseMockDir):
    def setUp(self):
        super(TestUpdateReadme, self).setUp()
        self.readme_template_file = "readme_template.md"
        self.readme_file = "readme.md"

    @mock.patch("helpers.load_sources_data")
    def test_update_content(self, mock_load_source_data):
        mock_load_source_data.return_value = [
            {
                "name": "HRS ad-hoc list",
                "description": "",
                "home_url": "",
                "frequency": "",
                "issues": "https://test",
                "url": "https://test",
                "license": "DBAD",
            },
        ]

        template_contents = """* Last updated: **@GEN_DATE@**.
* Here's the [raw hosts file](https://raw.githubusercontent.com/hrshadhin/hosts/master/@SUBFOLDER@hosts) containing @NUM_ENTRIES@ entries.
* This project is heavily inspired by [StevenBlack/hosts](https://github.com/StevenBlack/hosts/) project.

## Sources of hosts data unified in this variant

Updated `hosts` files from the following locations are always unified and included:

Host file source | Description | Home page | Raw hosts | Update frequency | License | Issues
-----------------|-------------|:---------:|:---------:|:----------------:|:-------:|:------:
@SOURCEROWS@
        """ # noqa:

        template_file = os.path.join(self.test_dir, self.readme_template_file)
        with open(template_file, "w") as f:
            f.writelines(template_contents)

        kwargs = dict(
            readme_file=self.readme_file,
            readme_template=template_file,
            number_of_rules=5,
            source_path="foobar/sources",
            source_info_file_name="info.json",
        )

        update_readme(kwargs)

        with open(self.readme_file, "r") as readme_file:
            contents = readme_file.read().rstrip()
            # Expected contents.
            for expected in (
                "## Sources of hosts data unified in this variant",
                " containing {count}".format(count=kwargs["number_of_rules"]),
                "Host file source",
                "HRS ad-hoc list",
                "DBAD",
            ):
                self.assertIn(expected, contents)

    def tearDown(self):
        super(TestUpdateReadme, self).tearDown()


if __name__ == "__main__":
    unittest.main()
