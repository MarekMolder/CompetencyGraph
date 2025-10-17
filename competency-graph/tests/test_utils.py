import unittest, asyncio
from unittest.mock import patch, Mock, AsyncMock

import aiohttp
import pytest
import requests
from IPython.core.ultratb import ListTB
from logic import graph_utils
from rdflib import URIRef, RDFS, Graph, Literal

SCHEMA = graph_utils.SCHEMA
BASE_RDF = graph_utils.BASE_RDF

class MyTestCase(unittest.TestCase):

    def test_urls_are_reachable(self):
        urls = [
            "https://schema.edu.ee/",
            "https://schema.org/",
            "https://oppekava.edu.ee/a/Special:ExportRDF/",
            "https://oppekava.edu.ee/a/",
            "https://oppekava.edu.ee/a/Kategooria:Haridus:Oskus",
            "https://oppekava.edu.ee/a/Kategooria:Haridus:Kompetents",
            "https://oppekava.edu.ee/a/Kategooria:Haridus:Tegevusnaitaja",
            "https://oppekava.edu.ee/a/Kategooria:Haridus:Knobit",
        ]
        for url in urls:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            self.assertEqual(resp.status_code, 200, f"Failed on {url}")

    def test_rdf_uris_are_valid_and_reachable(self):
        uris = [
            "http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3Aesco_link",
            "http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3Aesco_vaste",
            "http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3Aosk_reg_kood",
            "https://schema.edu.ee/verb",
            "http://oppekava.edu.ee/a/Special:URIResolver/Property-3ASchema-3ArelevantOccupation",
            "http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3AosaOskus",
            "http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3AeeldusOskus",
            "http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3Aseotud",
            "http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3AKompSisaldabTn",
            "http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3ATnSisaldabKnobitit",
            "http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3ATnEeldab",
            "http://oppekava.edu.ee/a/Special:URIResolver/Property-3AKnobitiLiik",
        ]
        for u in uris:
            ref = URIRef(u)
            assert str(ref).startswith("http")

            resp = requests.head(u, timeout=10, allow_redirects=True)
            assert resp.status_code < 500, f"Server error for {u}"

    def test_decode_smw_hex_nothing_to_decode(self):
        #Arrange
        raw = {
            "Oskus": "Oskus",
            "Oskus-20ABC": "Oskus-20ABC",
            "": ""
        }

        #Act & Assert
        for res, expected in raw.items():
            assert graph_utils.decode_smw_hex(res) == expected

    def test_decode_smw_hex_decode_comma(self):
        #Arrange
        raw = {
            "Oskus-2CABC": "Oskus,ABC",
            "A-2CB-2CC": "A,B,C",
        }

        #Act & Assert
        for res, expected in raw.items():
            assert graph_utils.decode_smw_hex(res) == expected

    def test_fix_decimal_commas_simple(self):
        #Arrange
        xml = b'<value datatype="http://www.w3.org/2001/XMLSchema#double">3,14</value>'
        expected = b'<value datatype="http://www.w3.org/2001/XMLSchema#double">3.14</value>'

        #Act & Assert
        assert graph_utils.fix_decimal_commas(xml) == expected

    def test_fix_decimal_commas_multiple_commas(self):
        #Arrange
        xml = b'<value datatype="http://www.w3.org/2001/XMLSchema#double">3,14,15</value>'
        expected = b'<value datatype="http://www.w3.org/2001/XMLSchema#double">3.14.15</value>'

        #Act & Assert
        assert graph_utils.fix_decimal_commas(xml) == expected

    def test_fix_decimal_commas_no_change_comma(self):
        #Arrange
        xml = b'<value datatype="http://www.w3.org/2001/XMLSchema#double">3.14</value>'

        #Act & Assert
        assert graph_utils.fix_decimal_commas(xml) == xml

    def test_fix_decimal_commas_no_change_integer(self):
        #Arrange
        xml = b'<value datatype="http://www.w3.org/2001/XMLSchema#double">34</value>'

        #Act & Assert
        assert graph_utils.fix_decimal_commas(xml) == xml

    def test_fix_decimal_commas_other_datatype_no_change(self):
        #Arrange
        xml = b'<value datatype="http://www.w3.org/2001/XMLSchema#string">3,14</value>'

        #Act & Assert
        assert graph_utils.fix_decimal_commas(xml) == xml

    def test_fix_decimal_commas_empty_content(self):
        #Arrange
        xml = b'<value datatype="http://www.w3.org/2001/XMLSchema#string"></value>'

        #Act & Assert
        assert graph_utils.fix_decimal_commas(xml) == xml

    def test_uri_to_skill_name(self):
        #Arrange
        raw = {
            "https://oppekava.edu.ee/a/Oskus": "Oskus",
            "https://oppekava.edu.ee/a/Oskus-2CABC": "Oskus,ABC",
            "https://oppekava.edu.ee/a/Oskus%20Test": "Oskus Test",
            "https://oppekava.edu.ee/a/Oskus-20ABC": "Oskus-20ABC",
            "https://oppekava.edu.ee/a/": ""
        }

        #Act & Assert
        for res, expected in raw.items():
            assert graph_utils.uri_to_skill_name(res) == expected

    def test_uri_to_label(self):
        #Arrange
        raw = {
            "https://oppekava.edu.ee/a/Probleemi_lahendus": "Probleemi lahendus",
            "https://oppekava.edu.ee/a/Tegevus-2CNaitaja_test": "Tegevus,Naitaja test",
            "https://oppekava.edu.ee/a/Oskus%20Test_ABC": "Oskus Test ABC",
            "https://oppekava.edu.ee/a/": ""
        }

        #Act & Assert
        for res, expected in raw.items():
            assert graph_utils.uri_to_label(res) == expected


    def test_normalize_key(self):
        #Arrange
        raw = {
            " Probleemilahendus ": "Probleemilahendus",
            "Oskus-2CABC" : "Oskus,ABC",
            "Oskus Test": "Oskus_Test",
            "Oskus___Test": "Oskus_Test",
            "Oskus(123)": "Oskus",
            " Oskus-2CTest(42) ": "Oskus,Test"
        }

        #Act & Assert
        for res, expected in raw.items():
            assert graph_utils.normalize_key(res) == expected

    @patch("logic.graph_utils.requests.get")
    def test_get_all_data_returns_links(self, mock_get):
        html = b"""
          <html><body>
              <a href="/a/Skill_One">Skill_One</a>
              <a href="/a/Skill_Two">Skill_Two</a>
              <a href="/a/Kategooria:Haridus">Category</a>
              <a href="/a/Eri:SpecialPage">Special</a>
          </body></html>
          """

        mock_response = Mock()
        mock_response.content = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        url = "https://example.com/test"
        result = graph_utils.get_all_data(url)

        self.assertIn("Skill_One", result)
        self.assertIn("Skill_Two", result)
        self.assertTrue(all("Kategooria" not in r for r in result))
        self.assertTrue(all("Eri:" not in r for r in result))

    async def test_cache_hit(self):
        # Paneme cache'i ette
        key = "rdf_v2:MySkill"
        graph_utils.CACHE.set(key, b"<rdf>3,14</rdf>")

        class DummySession:
            pass

        blob = await graph_utils._fetch_rdf(DummySession(), "MySkill")
        self.assertIn(b"3.14", blob)  # kontroll, et koma vahetati punktiks

    @patch("logic.graph_utils.aiohttp.ClientSession.get")
    async def test_http_success(self, mock_get):
        # Mockime aiohttp vastuse
        mock_resp = AsyncMock()
        mock_resp.read.return_value = b"<rdf>42,0</rdf>"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value.__aenter__.return_value = mock_resp

        async with aiohttp.ClientSession() as session:
            blob = await graph_utils._fetch_rdf(session, "MySkill2")
            self.assertIn(b"42.0", blob)

    @patch("logic.graph_utils.aiohttp.ClientSession.get")
    async def test_http_failure_then_retry(self, mock_get):
        # Esimene kord viskab vea, teine kord õnnestub
        bad_resp = AsyncMock()
        bad_resp.raise_for_status.side_effect = Exception("fail")
        good_resp = AsyncMock()
        good_resp.read.return_value = b"<rdf>99,9</rdf>"
        good_resp.raise_for_status = Mock()

        mock_get.return_value.__aenter__.side_effect = [bad_resp, good_resp]

        async with aiohttp.ClientSession() as session:
            blob = await graph_utils._fetch_rdf(session, "MySkill3")
            self.assertIn(b"99.9", blob)

    def test_parse_graph_from_bytes_simple(self):
        xml = b"""
          <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                   xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
            <rdf:Description rdf:about="http://example.com/Skill1">
              <rdfs:label>My Skill</rdfs:label>
            </rdf:Description>
          </rdf:RDF>
          """

        # Act
        g = graph_utils._parse_graph_from_bytes(xml)

        # Assert: graaf sisaldab seda subjecti ja labelit
        subj = URIRef("http://example.com/Skill1")
        labels = list(g.objects(subj, RDFS.label))

        self.assertEqual(len(labels), 1)
        self.assertEqual(str(labels[0]), "My Skill")

    def test_finds_subject_with_schema_name(self):
        # Arrange
        g = Graph()
        subj = URIRef("http://example.com/Skill1")
        g.add((subj, SCHEMA.name, Literal("My Skill")))
        g.add((subj, SCHEMA.description, Literal("A skill description")))

        # Act
        uri, desc = graph_utils._extract_subject_and_description(g, "My_Skill")

        # Assert
        self.assertEqual(uri, subj)
        self.assertEqual(desc, "A skill description")

    def test_finds_subject_with_rdfs_label(self):
        g = Graph()
        subj = URIRef("http://example.com/Skill2")
        g.add((subj, RDFS.label, Literal("Another Skill")))
        g.add((subj, SCHEMA.description, Literal("Second description")))

        uri, desc = graph_utils._extract_subject_and_description(g, "Another_Skill")

        self.assertEqual(uri, subj)
        self.assertEqual(desc, "Second description")

    def test_falls_back_to_base_uri(self):
        g = Graph()  # tühi graaf
        skill_name = "UnknownSkill"

        uri, desc = graph_utils._extract_subject_and_description(g, skill_name)

        self.assertEqual(uri, URIRef(BASE_RDF + skill_name))
        self.assertEqual(desc, "")

    @patch("logic.graph_utils._fetch_rdf")
    async def test_process_one_simple(self, mock_fetch):
        # RDF XML: 1 skill millel on üks subskill ja üks occupation
        xml = b"""
           <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                    xmlns:schema="https://schema.org/"
                    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
             <rdf:Description rdf:about="http://example.com/Skill1">
               <schema:name>My Skill</schema:name>
               <schema:description>Main skill desc</schema:description>
               <rdfs:label>My Skill</rdfs:label>
             </rdf:Description>
           </rdf:RDF>
           """
        mock_fetch.return_value = xml

        data = {}
        depths = {}
        visited = set()
        q = asyncio.Queue()

        async with graph_utils.aiohttp.ClientSession() as session:
            await graph_utils._process_one(session, "Skill1", 0, data, depths, q, visited)

        # Kontrollid
        self.assertIn("Skill1", str(data))  # node olemas
        self.assertEqual(depths["My_Skill"], 0)  # depth salvestatud
        self.assertEqual(data["My_Skill"]["description"], "Main skill desc")

    @patch("logic.graph_utils._fetch_rdf")
    async def test_process_one_full_graph(self, mock_fetch):
        # RDF XML näidis, kus:
        # - Skill1 on põhioskuse node
        # - Skill2 on subskill
        # - Skill3 on prerequisite
        # - Occup1 on seotud amet
        # - TN1 on tegevusnäitaja
        # - KN1 on knobit

        xml = """
           <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                    xmlns:schema="https://schema.org/"
                    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
                    xmlns:edu="https://schema.edu.ee/"
                    xmlns:ex="http://example.com/">
             <rdf:Description rdf:about="http://example.com/Skill1">
               <schema:name>Skill One</schema:name>
               <schema:description>Main skill desc</schema:description>
               <rdfs:label>Skill One</rdfs:label>

               <!-- subskill -->
               <edu:osaOskus rdf:resource="http://example.com/Skill2"/>

               <!-- prerequisite -->
               <edu:eeldusOskus rdf:resource="http://example.com/Skill3"/>

               <!-- occupation -->
               <schema:relevantOccupation rdf:resource="http://example.com/Occup1"/>

               <!-- tegevusnäitaja -->
               <edu:KompSisaldabTn rdf:resource="http://example.com/TN1"/>
             </rdf:Description>

             <!-- occupation node -->
             <rdf:Description rdf:about="http://example.com/Occup1">
               <rdfs:label>Occupation Label</rdfs:label>
             </rdf:Description>

             <!-- TN1 sisaldab knobit -->
             <rdf:Description rdf:about="http://example.com/TN1">
               <edu:TnSisaldabKnobitit rdf:resource="http://example.com/KN1"/>
             </rdf:Description>
           </rdf:RDF>
           """.encode("utf-8")

        mock_fetch.return_value = xml

        data = {}
        depths = {}
        visited = set()
        q = asyncio.Queue()

        async with aiohttp.ClientSession() as session:
            await graph_utils._process_one(
                session, "Skill1", 0, data, depths, q, visited
            )

        # Kontrollid: kas node loodi
        key = graph_utils.normalize_key("Skill1")
        self.assertIn(key, data)

        node = data[key]
        self.assertEqual(node["label"], "Skill One")
        self.assertEqual(node["description"], "Main skill desc")

        # Kontrolli, et väljad täituksid
        self.assertIn(graph_utils.normalize_key("Skill2"), node["subskills"])
        self.assertIn(graph_utils.normalize_key("Skill3"), node["prerequisites"])
        self.assertIn(graph_utils.normalize_key("TN1"), node["tegevusnaitajad"])
        self.assertIn(graph_utils.normalize_key("KN1"), node["knobitid"])

        # Kontrolli occupation
        occs = node["relevant_occupations"]
        self.assertEqual(len(occs), 1)
        self.assertEqual(occs[0]["label"], "Occupation Label")

        # Queue peaks sisaldama järgmise sügavuse nimesid
        queued = []
        while not q.empty():
            queued.append(await q.get())

        queued_names = {name for (name, depth) in queued}
        self.assertIn("Skill2", queued_names)
        self.assertIn("Skill3", queued_names)
        self.assertIn("TN1", queued_names)
        self.assertIn("KN1", queued_names)

    @patch("logic.graph_utils._process_one")
    async def test_simple_parse_all_data_async(self, mock_process_one):
        async def fake_process_one(session, skill_name, depth, data, depths, q, visited):
            data[skill_name] = {"label": skill_name}
            if skill_name == "Skill1":
                await q.put(("Skill2", depth + 1))

        mock_process_one.side_effect = fake_process_one

        data, depths = await graph_utils.parse_all_data_async(["Skill1"])

        self.assertIn("Skill1", data)
        self.assertIn("Skill2", data)

if __name__ == '__main__':
    unittest.main()
