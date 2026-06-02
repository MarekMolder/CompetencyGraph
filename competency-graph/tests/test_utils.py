"""Tests for helpers that remain in logic/graph_utils.py after the ask API migration.

Tests for the old RDF-XML fetcher (fix_decimal_commas, _fetch_rdf, _process_one,
_extract_subject_and_description, _parse_graph_from_bytes, the legacy
parse_all_data_async) were removed when that code was deleted. The ask API
client and its helpers are covered by tests/test_ask_api.py.
"""
import unittest

import requests

from logic import graph_utils


class MyTestCase(unittest.TestCase):

    def test_urls_are_reachable(self):
        urls = [
            "https://schema.edu.ee/",
            "https://schema.org/",
            "https://oppekava.edu.ee/a/",
            "https://oppekava.edu.ee/a/Kategooria:Haridus:Oskus",
            "https://oppekava.edu.ee/a/Kategooria:Haridus:Kompetents",
            "https://oppekava.edu.ee/a/Kategooria:Haridus:Tegevusnaitaja",
            "https://oppekava.edu.ee/a/Kategooria:Haridus:Knobit",
        ]
        for url in urls:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            self.assertEqual(resp.status_code, 200, f"Failed on {url}")

    def test_decode_smw_hex_nothing_to_decode(self):
        # decode_smw_hex decodes any printable ASCII (0x20..0x7E) hex escape,
        # including 0x20 (space). Strings without hex escapes pass through.
        raw = {"Oskus": "Oskus", "": ""}
        for res, expected in raw.items():
            assert graph_utils.decode_smw_hex(res) == expected

    def test_decode_smw_hex_decode_comma(self):
        raw = {"Oskus-2CABC": "Oskus,ABC", "A-2CB-2CC": "A,B,C"}
        for res, expected in raw.items():
            assert graph_utils.decode_smw_hex(res) == expected

    def test_uri_to_skill_name(self):
        # -20 SMW hex decodes to space (0x20) — same as %20 URL-decoding
        raw = {
            "https://oppekava.edu.ee/a/Oskus": "Oskus",
            "https://oppekava.edu.ee/a/Oskus-2CABC": "Oskus,ABC",
            "https://oppekava.edu.ee/a/Oskus%20Test": "Oskus Test",
            "https://oppekava.edu.ee/a/Oskus-20ABC": "Oskus ABC",
            "https://oppekava.edu.ee/a/": "",
        }
        for res, expected in raw.items():
            assert graph_utils.uri_to_skill_name(res) == expected

    def test_uri_to_label(self):
        raw = {
            "https://oppekava.edu.ee/a/Probleemi_lahendus": "Probleemi lahendus",
            "https://oppekava.edu.ee/a/Tegevus-2CNaitaja_test": "Tegevus,Naitaja test",
            "https://oppekava.edu.ee/a/Oskus%20Test_ABC": "Oskus Test ABC",
            "https://oppekava.edu.ee/a/": "",
        }
        for res, expected in raw.items():
            assert graph_utils.uri_to_label(res) == expected

    def test_normalize_key(self):
        # normalize_key strips only 1-2-digit trailing parens. 3+ digits stay.
        raw = {
            " Probleemilahendus ": "Probleemilahendus",
            "Oskus-2CABC": "Oskus,ABC",
            "Oskus Test": "Oskus_Test",
            "Oskus___Test": "Oskus_Test",
            "Oskus(12)": "Oskus",
            "Oskus(123)": "Oskus(123)",
            " Oskus-2CTest(42) ": "Oskus,Test",
        }
        for res, expected in raw.items():
            assert graph_utils.normalize_key(res) == expected


if __name__ == "__main__":
    unittest.main()
