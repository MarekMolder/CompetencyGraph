import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# --- Std lib / 3rd party ---
import time
import asyncio, aiohttp, async_timeout
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote

from aiolimiter import AsyncLimiter
from diskcache import Cache

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDFS

from pyvis.network import Network
import networkx as nx

import re

# =========================
#      CONSTANTS / RDF
# =========================
EDU = Namespace("https://schema.edu.ee/")
SCHEMA = Namespace("https://schema.org/")
BASE_RDF = "https://oppekava.edu.ee/a/Special:ExportRDF/"
DISPLAY_URL = "https://oppekava.edu.ee/a/"
SKILLS_URL = "https://oppekava.edu.ee/a/Kategooria:Haridus:Oskus"

ESCO_LINK = URIRef("http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3Aesco_link")
ESCO_VASTE = URIRef("http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3Aesco_vaste")
OSK_REG_KOOD = URIRef("http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3Aosk_reg_kood")
VERB = URIRef("https://schema.edu.ee/verb")

OSAOSKUS = URIRef("http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3AosaOskus")
SEOTUD_OSKUS = URIRef("http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3AeeldusOskus")
SEOTUD = URIRef("http://oppekava.edu.ee/a/Special:URIResolver/Property-3AHaridus-3Aseotud")
EELDAB = URIRef("http://oppekava.edu.ee/a/Property:Haridus:eeldab")

# =========================
#   CONFIGURATION FLAGS
# =========================
LIMIT_RECURSION = False
MAX_DEPTH = 999_999_999
EXPORT_GRAPHML = True

# --- Async loader config ---
MAX_CONCURRENCY = 32          # mitu RDF päringut korraga
REQS_PER_SEC = 8              # kiirus serveri vastu
HTTP_TIMEOUT_SEC = 15
RETRIES = 4                   # eksponentsiaalne backoff
CACHE_TTL = 60 * 60 * 24 * 14 # 14 päeva

CACHE = Cache("./rdf_cache")
SEM = asyncio.Semaphore(MAX_CONCURRENCY)
RATE = AsyncLimiter(REQS_PER_SEC, time_period=1)
HEADERS = {
    "User-Agent": "skills-crawler/1.0 (+contact: you@example.com)",
    "Accept-Encoding": "gzip, deflate",
}

# =========================
#       UTILITIES
# =========================

DOUBLE_TAG_RE = re.compile(
    rb'(<[^>]*datatype\s*=\s*(?:"|\')http://www\.w3\.org/2001/XMLSchema#double(?:"|\')[^>]*>)([\s\S]*?)(</\s*[^>]+>)',
    re.IGNORECASE
)

def _fix_decimal_commas(xml_bytes: bytes) -> bytes:
    """
    Asendab xsd:double elementide TEXT-is koma punktiga.
    Ei puutu teisi elemente. Teeme seda ka cache-hit'i puhul.
    """
    def _repl(m):
        open_tag = m.group(1)
        content  = m.group(2)
        close_tag= m.group(3)
        # Vahel on seal whitespace’e – kärbime servad, aga säilitame algse spacing’u
        # Lihtne strateegia: asenda kõik komad punktidega sisu sees
        fixed = content.replace(b',', b'.')
        return open_tag + fixed + close_tag

    return DOUBLE_TAG_RE.sub(_repl, xml_bytes)

def uri_to_skill_name(uri: str) -> str:
    return unquote(uri.split("/")[-1])

def uri_to_label(uri: str) -> str:
    return unquote(uri.split("/")[-1].replace("_", " "))

def _skill_key(skill_name: str) -> str:
    return skill_name.strip()

# =========================
#       SCRAPER
# =========================
def get_all_skills(category_url: str):
    """
    Loeb kategoorialehelt oskuste ID-d (URL-i viimased osad).
    """
    skills = set()
    try:
        response = requests.get(category_url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        for link in soup.select("ul li a"):
            href = link.get("href")
            if href and href.startswith("/a/") and ":" not in href:
                skill = href.split("/a/")[-1]
                skills.add(skill)
        print(f"Found {len(skills)} skills")
    except Exception as e:
        print(f"Error retrieving skills: {e}")
    return list(skills)

# =========================
#    ASYNC RDF LOADING
# =========================
async def _fetch_rdf(session: aiohttp.ClientSession, skill_name: str) -> bytes:
    """
    Võrgupäring RDF-XML-ile koos ketta-cache, paralleelsuse ja backoffiga.
    """
    cache_key = f"rdf_v2:{skill_name}"
    cached = CACHE.get(cache_key)
    if cached is not None:
        # ka hit'i puhul jookse läbi fix (kui mõni vana v2 sisse satub)
        fixed = _fix_decimal_commas(cached)
        if fixed != cached:
            CACHE.set(cache_key, fixed, expire=CACHE_TTL)
        return fixed

    url = BASE_RDF + skill_name
    async with SEM, RATE:
        for attempt in range(RETRIES):
            try:
                async with async_timeout.timeout(HTTP_TIMEOUT_SEC):
                    async with session.get(url, headers=HEADERS, ssl=False) as resp:
                        resp.raise_for_status()
                        blob = await resp.read()
                        blob = _fix_decimal_commas(blob)  # ⬅️ parandame ENNE cache’i
                        CACHE.set(cache_key, blob, expire=CACHE_TTL)
                        return blob
            except Exception:
                await asyncio.sleep(0.5 * (2 ** attempt))
        raise RuntimeError(f"Failed to fetch {skill_name} after {RETRIES} attempts")

def _parse_graph_from_bytes(xml_bytes: bytes) -> Graph:
    g = Graph()
    g.parse(data=xml_bytes, format="xml")
    return g

def _extract_subject_and_description(g: Graph, skill_name: str):
    subject_uri = None
    description = ""
    label_match = uri_to_label(skill_name).lower()

    for s in g.subjects(predicate=SCHEMA.name):
        name_val = str(g.value(s, SCHEMA.name, default="")).strip().lower()
        if name_val == label_match:
            subject_uri = s
            description = str(g.value(s, SCHEMA.description, default=""))
            break

    if subject_uri is None:
        for s in g.subjects(predicate=RDFS.label):
            name_val = str(g.value(s, RDFS.label, default="")).strip().lower()
            if name_val == label_match:
                subject_uri = s
                description = str(g.value(s, SCHEMA.description, default=""))
                break

    if subject_uri is None:
        subject_uri = URIRef(BASE_RDF + skill_name)

    return subject_uri, description

async def _process_one(session: aiohttp.ClientSession, skill_name: str, depth: int,
                       data: dict, depths: dict, q: asyncio.Queue, visited: set):
    """
    Laeb ühe oskuse RDF-i, täidab väljad ja lisab järgmiseks sammuks naabrite nimed järjekorda.
    """
    try:
        xml = await _fetch_rdf(session, skill_name)
        g_rdf = _parse_graph_from_bytes(xml)
        subject_uri, description = _extract_subject_and_description(g_rdf, skill_name)

        label = uri_to_label(skill_name)
        depths[label] = min(depth, depths.get(label, depth))

        node = data.get(label)
        if not node:
            node = data[label] = {
                "uri": subject_uri,
                "description": description,
                "link": DISPLAY_URL + skill_name,
                "subskills": [],
                "prerequisites": [],
                "competency": [],
                "esco_link": str(g_rdf.value(subject_uri, ESCO_LINK, default="")),
                "esco_vaste": str(g_rdf.value(subject_uri, ESCO_VASTE, default="")),
                "osk_reg_kood": str(g_rdf.value(subject_uri, OSK_REG_KOOD, default="")),
                "skill_verb": str(g_rdf.value(subject_uri, VERB, default="")),
            }

        # 1) alla: osaoskused
        for o in g_rdf.objects(subject=subject_uri, predicate=OSAOSKUS):
            sub_uri = str(o)
            sub_name = uri_to_skill_name(sub_uri)
            sub_label = uri_to_label(sub_uri)
            if sub_label not in node["subskills"]:
                node["subskills"].append(sub_label)
            key = _skill_key(sub_name)
            if not LIMIT_RECURSION or depth + 1 <= MAX_DEPTH:
                if key not in visited:
                    visited.add(key)
                    await q.put((sub_name, depth + 1))

        # 2) üles: koosneja
        for s in g_rdf.subjects(predicate=OSAOSKUS, object=subject_uri):
            parent_name = uri_to_skill_name(str(s))
            key = _skill_key(parent_name)
            if not LIMIT_RECURSION or depth + 1 <= MAX_DEPTH:
                if key not in visited:
                    visited.add(key)
                    await q.put((parent_name, depth + 1))

        # 3) alla: eeldusOskus
        for o in g_rdf.objects(subject=subject_uri, predicate=SEOTUD_OSKUS):
            pre_uri = str(o)
            pre_name = uri_to_skill_name(pre_uri)
            pre_label = uri_to_label(pre_uri)
            if pre_label not in node["prerequisites"]:
                node["prerequisites"].append(pre_label)
            key = _skill_key(pre_name)
            if not LIMIT_RECURSION or depth + 1 <= MAX_DEPTH:
                if key not in visited:
                    visited.add(key)
                    await q.put((pre_name, depth + 1))

        # 4) üles: eeldusOskus
        for s in g_rdf.subjects(predicate=SEOTUD_OSKUS, object=subject_uri):
            parent_name = uri_to_skill_name(str(s))
            key = _skill_key(parent_name)
            if not LIMIT_RECURSION or depth + 1 <= MAX_DEPTH:
                if key not in visited:
                    visited.add(key)
                    await q.put((parent_name, depth + 1))

        # 5) seotud / õpiväljund (EDU.eeldab)
        for o in g_rdf.objects(subject=subject_uri, predicate=EDU.eeldab):
            rel_uri = str(o)
            rel_name = uri_to_skill_name(rel_uri)
            rel_label = uri_to_label(rel_uri)
            if rel_label not in node["competency"]:
                node["competency"].append(rel_label)
            key = _skill_key(rel_name)
            if not LIMIT_RECURSION or depth + 1 <= MAX_DEPTH:
                if key not in visited:
                    visited.add(key)
                    await q.put((rel_name, depth + 1))

        # 6) üles: EDU.eeldab
        for s in g_rdf.subjects(predicate=EDU.eeldab, object=subject_uri):
            parent_name = uri_to_skill_name(str(s))
            key = _skill_key(parent_name)
            if not LIMIT_RECURSION or depth + 1 <= MAX_DEPTH:
                if key not in visited:
                    visited.add(key)
                    await q.put((parent_name, depth + 1))

    except Exception as e:
        print(f"[warn] {skill_name}: {e}")

async def parse_all_skills_async(skill_list):
    """
    Asünkroonne 'kogu graafi' kraapimine paralleelselt, külastatud-set kaitsega.
    NB! Kui sisend on väga suur, on see siiski raske; aga kordades kiirem kui sünkroonne.
    """
    data, depths = {}, {}
    visited = set()
    q: asyncio.Queue = asyncio.Queue()

    # esmane seeme
    for s in skill_list:
        key = _skill_key(s)
        if key not in visited:
            visited.add(key)
            q.put_nowait((s, 0))

    async with aiohttp.ClientSession() as session:
        async def worker():
            while True:
                try:
                    skill_name, depth = await q.get()
                except asyncio.CancelledError:
                    return
                await _process_one(session, skill_name, depth, data, depths, q, visited)
                q.task_done()

        workers = [asyncio.create_task(worker()) for _ in range(MAX_CONCURRENCY)]
        await q.join()
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

    sample = list(data.keys())[:10]
    print(f"✅ Andmestikus olevad oskused: {sample}")
    if "Probleemilahendus" not in data:
        print("❌ Probleemilahendus puudub data-s!")

    return data, depths

# =========================
#     VISUALIZATION
# =========================
def build_interactive_graph(data, depths, filename="skill_graph.html"):
    net = Network(height="100vh", width="100%", directed=True)
    _set_network_options(net)
    _add_nodes(net, data, depths)
    _add_edges(net, data)
    net.write_html(filename)
    _inject_html_controls(filename, depths)

def _set_network_options(net):
    net.set_options("""
    const options = {
      "nodes": {
        "shape": "dot",
        "scaling": {"min": 10, "max": 30},
        "font": {"size": 16, "face": "Arial", "color": "#343434"},
        "borderWidth": 2
      },
      "edges": {
        "arrows": {"to": {"enabled": true, "scaleFactor": 0.8}},
        "color": {"color": "#cccccc", "highlight": "#999999"},
        "width": 1.5,
        "smooth": {"enabled": true, "type": "dynamic", "roundness": 0.3}
      },
      "physics": {
        "forceAtlas2Based": {"gravitationalConstant": -80, "springLength": 110, "springConstant": 0.05},
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 200,
        "navigationButtons": true,
        "keyboard": true,
        "multiselect": true,
        "zoomView": true
      },
      "layout": {"improvedLayout": true}
    }
    """)

def _add_nodes(net, data, depths):
    for label, info in data.items():
        level = depths.get(label, 0)
        size = 10 + len(info.get("subskills", [])) * 1.5

        # Parandatud värviloogika: kasutame reaalseid võtmeid (prerequisites/competency/subskills)
        if info.get("prerequisites"):
            color = "#a1c9f1"   # hele sinine – eeldused
        elif info.get("competency"):
            color = "#58a55c"   # rohekas – seotud/õpiväljund
        elif info.get("subskills"):
            color = "#bf98e6"   # lilla – osaoskus
        else:
            color = "#b7e1cd"   # vaikimisi

        net.add_node(
            label,
            label=label,
            title=f"Skill: {label}\nDescription: {info.get('description','')}\nClick me!",
            shape="dot",
            size=size,
            level=level,
            link=info.get("link",""),
            color=color
        )

def _add_edges(net, data):
    added_edges = set()
    for label, info in data.items():
        edge_types = [
            ("subskills", "#2b7bba"),     # blue
            ("prerequisites", "#2980b9"), # dark blue
            ("competency", "#58a55c"),    # green
        ]
        for key, color in edge_types:
            for target in info.get(key, []):
                if target in data:
                    edge = (target, label, color)
                    if edge not in added_edges:
                        net.add_edge(source=target, to=label, color=color)
                        added_edges.add(edge)

def _inject_html_controls(filename, depths):
    with open(filename, "r", encoding="utf-8") as f:
        html = f.read()

    levels = sorted(set(depths.values()))
    filter_controls = "\n".join([
        f'<label><input type="checkbox" id="toggleLevel{lvl}" checked onchange="toggleLevel({lvl})"> Level {lvl}</label><br>'
        for lvl in levels
    ])

    custom_html = f"""
    <style>
      #controls {{ position: fixed; top: 10px; left: 10px; z-index: 1000; background: #fff;
                  padding: 10px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
    </style>
    <div id="controls">
      <input type="text" id="searchBox" placeholder="Search skill..." oninput="searchNode()" />
      <br><br>
      {filter_controls}
    </div>
    <script>
    function searchNode() {{
        var term = document.getElementById("searchBox").value.toLowerCase();
        nodes.get().forEach(function(n) {{
            var visible = n.label.toLowerCase().includes(term);
            nodes.update({{id: n.id, hidden: !visible}});
        }});
    }}
    function toggleLevel(level) {{
        var checked = document.getElementById("toggleLevel" + level).checked;
        nodes.get().forEach(function(n) {{
            if (n.level === level) {{
                nodes.update({{id: n.id, hidden: !checked}});
            }}
        }});
    }}
    network.on("click", function (params) {{
        if (params.nodes.length > 0) {{
            var nodeId = params.nodes[0];
            var node = nodes.get(nodeId);
            if (node.link) {{
                window.open(node.link, "_blank");
            }}
        }}
    }});
    </script>
    </body>"""

    html = html.replace("</body>", custom_html)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

def export_graphml(data, filename="skills_graph.graphml"):
    g = nx.DiGraph()
    for label, info in data.items():
        g.add_node(label, description=info.get("description",""), link=info.get("link",""))
        for sub in info.get("subskills", []):
            g.add_edge(sub, label)
    nx.write_graphml(g, filename)
    print(f"GraphML exported: {filename}")

# =========================
#        MAIN
# =========================
if __name__ == "__main__":
    skills = get_all_skills(SKILLS_URL)

    # UUS: asünkroonne täisgraafi laadimine (paralleel + cache)
    parsed_data, depths = asyncio.run(parse_all_skills_async(skills))

    build_interactive_graph(parsed_data, depths)
    if EXPORT_GRAPHML:
        export_graphml(parsed_data)

parse_all_skills_recursive = parse_all_skills_async