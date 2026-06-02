"""Tests for logic/ask_api.py — SMW ask API client."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import unquote

from logic import ask_api


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name: str) -> dict:
    with open(os.path.join(FIXTURES_DIR, name), encoding="utf-8") as f:
        return json.load(f)


class TestBuildQuery(unittest.TestCase):

    def test_build_query_has_base_url_and_action(self):
        url = ask_api.build_query("Haridus:Oskus", ["Schema:description"])
        self.assertTrue(url.startswith(ask_api.BASE_URL))
        self.assertIn("action=ask", url)
        self.assertIn("format=json", url)

    def test_build_query_includes_category_constraint(self):
        url = ask_api.build_query("Haridus:Oskus", [])
        self.assertIn("[[Category:Haridus:Oskus]]", unquote(url))

    def test_build_query_includes_each_attr_as_printout(self):
        url = ask_api.build_query(
            "Haridus:Oskus",
            ["Schema:description", "Haridus:esco_link"],
        )
        decoded = unquote(url)
        self.assertIn("?Schema:description", decoded)
        self.assertIn("?Haridus:esco_link", decoded)

    def test_build_query_includes_limit_and_offset(self):
        url = ask_api.build_query("Haridus:Oskus", [], offset=500, limit=200)
        decoded = unquote(url)
        self.assertIn("limit=200", decoded)
        self.assertIn("offset=500", decoded)


class TestParsePageOccupationsAndEdges(unittest.TestCase):

    def test_parse_page_relevant_occupations(self):
        page_data = {
            "printouts": {"Schema:relevantOccupation": [
                {"fulltext": "Õpetaja", "fullurl": "https://oppekava.edu.ee/a/Opetaja"},
                {"fulltext": "Bioloog", "fullurl": "https://oppekava.edu.ee/a/Bioloog"},
            ]},
            "fullurl": "",
        }
        node = ask_api.parse_page_to_node("X", page_data, "oskus")
        self.assertEqual(len(node["relevant_occupations"]), 2)
        self.assertEqual(node["relevant_occupations"][0]["label"], "Õpetaja")
        self.assertEqual(node["relevant_occupations"][0]["uri"],
                         "https://oppekava.edu.ee/a/Opetaja")

    def test_parse_page_edge_osaoskus(self):
        page_data = {
            "printouts": {"Haridus:osaOskus": [
                {"fulltext": "Subskill_One", "fullurl": ""}
            ]},
            "fullurl": "",
        }
        node = ask_api.parse_page_to_node("Parent", page_data, "oskus")
        self.assertIn("Subskill_One", node["OSAOSKUS"])

    def test_parse_page_edge_eeldab_capitalized_by_api(self):
        # Default-namespace property "eeldab" comes back as "Eeldab" from the API
        page_data = {
            "printouts": {"Eeldab": [
                {"fulltext": "Prereq_OV", "fullurl": ""}
            ]},
            "fullurl": "",
        }
        node = ask_api.parse_page_to_node("OV1", page_data, "opivaljund")
        self.assertIn("Prereq_OV", node["OV_EELDAB"])

    def test_parse_page_multiple_edges_same_relation(self):
        page_data = {
            "printouts": {"Haridus:KompSisaldabTn": [
                {"fulltext": "TN_A", "fullurl": ""},
                {"fulltext": "TN_B", "fullurl": ""},
            ]},
            "fullurl": "",
        }
        node = ask_api.parse_page_to_node("Komp1", page_data, "kompetents")
        self.assertEqual(sorted(node["KOMP_SISALDAB_TN"]), ["TN_A", "TN_B"])

    def test_parse_page_edge_target_normalized(self):
        page_data = {
            "printouts": {"Haridus:osaOskus": [
                {"fulltext": "Skill With Spaces", "fullurl": ""}
            ]},
            "fullurl": "",
        }
        node = ask_api.parse_page_to_node("Parent", page_data, "oskus")
        # normalize_key turns "Skill With Spaces" -> "Skill_With_Spaces"
        self.assertIn("Skill_With_Spaces", node["OSAOSKUS"])


class TestParsePageToNode(unittest.TestCase):

    def test_parse_page_basic_fields(self):
        page_data = {
            "printouts": {"Schema:description": ["A skill."]},
            "fullurl": "https://oppekava.edu.ee/a/Probleemilahendus",
        }
        node = ask_api.parse_page_to_node("Probleemilahendus", page_data, "oskus")
        self.assertEqual(node["label"], "Probleemilahendus")
        self.assertEqual(node["description"], "A skill.")
        self.assertEqual(node["link"], "https://oppekava.edu.ee/a/Probleemilahendus")
        self.assertEqual(node["esco_link"], "")
        self.assertEqual(node["klass"], "")

    def test_parse_page_scalar_attr_string(self):
        page_data = {
            "printouts": {"Haridus:esco_link": ["http://esco.example/skill1"]},
            "fullurl": "",
        }
        node = ask_api.parse_page_to_node("Skill1", page_data, "oskus")
        self.assertEqual(node["esco_link"], "http://esco.example/skill1")

    def test_parse_page_scalar_attr_with_space_in_key(self):
        # The real SMW API returns "Haridus:esco link" (space, not underscore)
        page_data = {
            "printouts": {"Haridus:esco link": ["http://esco.example/skill2"]},
            "fullurl": "",
        }
        node = ask_api.parse_page_to_node("Skill2", page_data, "oskus")
        self.assertEqual(node["esco_link"], "http://esco.example/skill2")

    def test_parse_page_scalar_attr_dict_with_fulltext(self):
        page_data = {
            "printouts": {"Haridus:seotud oppeaine": [
                {"fulltext": "Bioloogia", "fullurl": "https://x/Bioloogia"}
            ]},
            "fullurl": "",
        }
        node = ask_api.parse_page_to_node("X", page_data, "opivaljund")
        self.assertEqual(node["seotud_oppeaine"], "Bioloogia")

    def test_parse_page_empty_printouts(self):
        node = ask_api.parse_page_to_node(
            "Empty", {"printouts": {}, "fullurl": ""}, "oskus"
        )
        for field in ask_api.SCALAR_PRINTOUT_TO_FIELD.values():
            self.assertEqual(node[field], "", f"Field {field} not empty")
        self.assertEqual(node["description"], "")

    def test_parse_page_label_underscores_to_spaces(self):
        node = ask_api.parse_page_to_node(
            "Multi_Word_Title", {"printouts": {}, "fullurl": ""}, "oskus"
        )
        self.assertEqual(node["label"], "Multi Word Title")


class TestGetAllData(unittest.TestCase):

    @patch("logic.ask_api._http_get_json_sync")
    def test_get_all_data_returns_normalized_keys(self, mock_get):
        mock_get.return_value = {
            "query": {"results": {
                "Skill_One": {"printouts": {}, "fullurl": ""},
                "Skill Two": {"printouts": {}, "fullurl": ""},
            }}
        }
        result = ask_api.get_all_data(
            "https://oppekava.edu.ee/a/Kategooria:Haridus:Oskus"
        )
        self.assertIn("Skill_One", result)
        self.assertIn("Skill_Two", result)

    @patch("logic.ask_api._http_get_json_sync")
    def test_get_all_data_paginates(self, mock_get):
        with patch.object(ask_api, "PAGE_SIZE", 2):
            page1 = {"query": {"results": {
                "A": {"printouts": {}, "fullurl": ""},
                "B": {"printouts": {}, "fullurl": ""},
            }}}
            page2 = {"query": {"results": {"C": {"printouts": {}, "fullurl": ""}}}}
            mock_get.side_effect = [page1, page2]
            result = ask_api.get_all_data(
                "https://oppekava.edu.ee/a/Kategooria:Haridus:Oskus"
            )
        self.assertEqual(sorted(result), ["A", "B", "C"])

    def test_get_all_data_unknown_category_url_returns_empty(self):
        result = ask_api.get_all_data("https://nowhere.invalid/foo")
        self.assertEqual(result, [])


class TestParseAllDataAsync(unittest.IsolatedAsyncioTestCase):

    @patch("logic.ask_api.fetch_category", new_callable=AsyncMock)
    async def test_parse_all_merges_categories(self, mock_fetch):
        async def fake_fetch(category, attrs, node_type, session=None):
            if node_type == "oskus":
                return {"Skill_A": {"label": "A", "OSAOSKUS": ["Skill_B"]}}
            if node_type == "kompetents":
                return {"Skill_B": {"label": "B"}}
            return {}
        mock_fetch.side_effect = fake_fetch

        data, depths = await ask_api.parse_all_data_async(["Skill_A"])
        self.assertIn("Skill_A", data)
        self.assertIn("Skill_B", data)
        self.assertEqual(depths["Skill_A"], 0)
        self.assertEqual(depths["Skill_B"], 1)

    @patch("logic.ask_api.fetch_category", new_callable=AsyncMock)
    async def test_parse_all_normalizes_keys(self, mock_fetch):
        async def fake_fetch(category, attrs, node_type, session=None):
            if node_type == "oskus":
                return {"Skill With Spaces": {"label": "x"}}
            return {}
        mock_fetch.side_effect = fake_fetch
        data, _ = await ask_api.parse_all_data_async(["Skill_With_Spaces"])
        self.assertIn("Skill_With_Spaces", data)

    @patch("logic.ask_api.fetch_category", new_callable=AsyncMock)
    async def test_parse_all_returns_empty_when_no_seed_matches(self, mock_fetch):
        async def fake_fetch(category, attrs, node_type, session=None):
            return {"Skill_A": {"label": "A"}}
        mock_fetch.side_effect = fake_fetch
        data, depths = await ask_api.parse_all_data_async(["UnknownSeed"])
        self.assertEqual(data, {})
        self.assertEqual(depths, {})


class TestBFS(unittest.TestCase):

    def _make_data(self):
        return {
            "A": {"OSAOSKUS": ["B"], "EELDUS_OSKUS": ["D"]},
            "B": {"OSAOSKUS": ["C"]},
            "C": {},
            "D": {},
            "E": {},
        }

    def test_bfs_reachable_only(self):
        data = self._make_data()
        filtered, _ = ask_api._bfs_filter(data, seeds=["A"])
        self.assertEqual(set(filtered.keys()), {"A", "B", "C", "D"})
        self.assertNotIn("E", filtered)

    def test_bfs_depths(self):
        data = self._make_data()
        _, depths = ask_api._bfs_filter(data, seeds=["A"])
        self.assertEqual(depths["A"], 0)
        self.assertEqual(depths["B"], 1)
        self.assertEqual(depths["D"], 1)
        self.assertEqual(depths["C"], 2)

    def test_bfs_multiple_seeds(self):
        data = self._make_data()
        filtered, depths = ask_api._bfs_filter(data, seeds=["A", "E"])
        self.assertEqual(set(filtered.keys()), {"A", "B", "C", "D", "E"})
        self.assertEqual(depths["E"], 0)

    def test_bfs_respects_max_depth(self):
        data = self._make_data()
        filtered, _ = ask_api._bfs_filter(
            data, seeds=["A"], limit_recursion=True, max_depth=1
        )
        self.assertEqual(set(filtered.keys()), {"A", "B", "D"})

    def test_bfs_seed_not_in_data_ignored(self):
        data = self._make_data()
        filtered, depths = ask_api._bfs_filter(data, seeds=["NoSuchKey"])
        self.assertEqual(filtered, {})
        self.assertEqual(depths, {})

    def test_bfs_follows_all_relation_keys(self):
        data = {
            "X": {"OPPEKAVA_OPPVALJUND": ["Y"], "TN_MOODAB_OV": ["Z"]},
            "Y": {}, "Z": {},
        }
        filtered, _ = ask_api._bfs_filter(data, seeds=["X"])
        self.assertEqual(set(filtered.keys()), {"X", "Y", "Z"})


class TestFetchCategory(unittest.IsolatedAsyncioTestCase):

    @patch("logic.ask_api._http_get_json", new_callable=AsyncMock)
    async def test_fetch_category_single_page(self, mock_get):
        mock_get.return_value = {
            "query": {"results": {
                "Skill_A": {
                    "printouts": {"Schema:description": ["A"]},
                    "fullurl": "https://x/Skill_A",
                },
            }}
        }
        nodes = await ask_api.fetch_category(
            "Haridus:Oskus", ["Schema:description"], "oskus"
        )
        self.assertEqual(len(nodes), 1)
        self.assertIn("Skill_A", nodes)
        self.assertEqual(nodes["Skill_A"]["description"], "A")
        self.assertEqual(mock_get.call_count, 1)

    @patch("logic.ask_api._http_get_json", new_callable=AsyncMock)
    @patch("logic.ask_api.PAGE_SIZE", 2)
    async def test_fetch_category_paginates(self, mock_get):
        page1 = {"query": {"results": {
            "A": {"printouts": {}, "fullurl": ""},
            "B": {"printouts": {}, "fullurl": ""},
        }}}
        page2 = {"query": {"results": {
            "C": {"printouts": {}, "fullurl": ""},
        }}}
        mock_get.side_effect = [page1, page2]
        nodes = await ask_api.fetch_category("Haridus:Oskus", [], "oskus")
        self.assertEqual(sorted(nodes.keys()), ["A", "B", "C"])
        self.assertEqual(mock_get.call_count, 2)


class TestParseFixture(unittest.TestCase):

    def test_parse_oskus_fixture(self):
        data = _load_fixture("ask_response_oskus.json")
        results = data["query"]["results"]
        self.assertGreater(len(results), 0, "Fixture has no results")
        for page_title, page_data in results.items():
            node = ask_api.parse_page_to_node(page_title, page_data, "oskus")
            self.assertIn("label", node)
            self.assertIn("description", node)
            self.assertIn("link", node)
            self.assertIn("relevant_occupations", node)
            self.assertTrue(node["label"])

    def test_parse_oskus_fixture_extracts_description(self):
        # At least one result in the fixture has a Schema:description value
        data = _load_fixture("ask_response_oskus.json")
        results = data["query"]["results"]
        descriptions = [
            ask_api.parse_page_to_node(t, d, "oskus")["description"]
            for t, d in results.items()
        ]
        self.assertTrue(any(descriptions),
                        f"No description extracted from fixture; got {descriptions}")

    def test_parse_opivaljund_fixture(self):
        data = _load_fixture("ask_response_opivaljund.json")
        results = data["query"]["results"]
        self.assertGreater(len(results), 0)
        for page_title, page_data in results.items():
            node = ask_api.parse_page_to_node(page_title, page_data, "opivaljund")
            self.assertIn("klass", node)
            self.assertIn("kooliaste", node)


if __name__ == "__main__":
    unittest.main()
