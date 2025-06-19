import requests
from bs4 import BeautifulSoup
from rdflib import Graph, Namespace
from urllib.parse import unquote
from pyvis.network import Network
import networkx as nx
from rdflib import URIRef
from rdflib.namespace import RDFS


"""
This section defines the key URIs and RDF namespaces used in the skills graph project.

- EDU: A custom RDF namespace from schema.edu.ee, used to access properties like 'koosneb' (consists of).
- SCHEMA: Standard schema.org namespace for extracting labels and descriptions of skills.
- BASE_RDF: Base URI to fetch RDF/XML data for a given skill page.
- DISPLAY_URL: Used to generate clickable links in the visual graph that lead to the actual skill page.
- SKILLS_URL: The page listing all skills, used to retrieve the initial list of skill entries.
"""
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


"""
Configuration flags:

- LIMIT_RECURSION: If True, limits the depth of recursive skill parsing to avoid overly deep graphs.
- MAX_DEPTH: The maximum depth allowed when LIMIT_RECURSION is enabled.
- EXPORT_GRAPHML: If True, the final graph will also be exported in GraphML format (for external tools like Gephi).
"""
LIMIT_RECURSION = False
MAX_DEPTH = 999999999999999999
EXPORT_GRAPHML = True


def uri_to_skill_name(uri):
    """
       This function is used to convert a full URI (e.g., 'https://oppekava.edu.ee/a/Loogiline_mõtlemine')
       into its skill identifier part (e.g., 'Loogiline_mõtlemine'), which is needed for RDF fetching and parsing.
    """
    return unquote(uri.split("/")[-1])


def uri_to_label(uri):
    """
        This is used to display skill names nicely in the visual graph (e.g., turning 'Loogiline_mõtlemine'
        into 'Loogiline mõtlemine').
    """
    return unquote(uri.split("/")[-1].replace("_", " "))


def get_all_skills(category_url):
    """
        Scrapes and collects all skill identifiers from a given category page on oppekava.edu.ee.

        This function makes an HTTP request to a category page listing educational skills,
        parses the HTML content to find links to individual skill pages, and extracts their identifiers.
        Only valid skill page links (under /a/ and not containing a colon) are considered.
    """
    skills = set()
    try:
        response = requests.get(category_url)
        soup = BeautifulSoup(response.content, "html.parser")
        for link in soup.select("ul li a"):
            href = link.get("href")
            if href and href.startswith("/a/") and ":" not in href:
                skill = href.split("/a/")[-1]
                skills.add(skill)
        print(f"Found {len(skills)} skills")
    except Exception as e:
        print(f"Error retrieving skills from category page: {e}")
    return list(skills)


def parse_all_skills_recursive(skill_list):
    """
        Recursively parses RDF data for each skill and builds a dictionary of skill relationships.

        For each skill, this function loads RDF data from the oppekava.edu.ee endpoint, extracts the label,
        description, and its subskills (if any), and stores them in a structured format.
        It also tracks the recursion depth for each skill to allow visual grouping later.
    """
    data = {}
    depths = {}

    def loader(skill_name, depth=0):
        label = uri_to_label(skill_name)
        if label in data or (LIMIT_RECURSION and depth > MAX_DEPTH):
            return

        try:
            g_rdf = Graph()
            g_rdf.parse(BASE_RDF + skill_name, format="xml")

            subject_uri = None
            description = ""
            label_match = uri_to_label(skill_name).lower()

            for s in g_rdf.subjects(predicate=SCHEMA.name):
                name_val = str(g_rdf.value(s, SCHEMA.name, default="")).strip().lower()
                if name_val == label_match:
                    subject_uri = s
                    description = str(g_rdf.value(s, SCHEMA.description, default=""))
                    break

            if subject_uri is None:
                for s in g_rdf.subjects(predicate=RDFS.label):
                    name_val = str(g_rdf.value(s, RDFS.label, default="")).strip().lower()
                    if name_val == label_match:
                        subject_uri = s
                        description = str(g_rdf.value(s, SCHEMA.description, default=""))
                        break


            if subject_uri is None:
                subject_uri = URIRef(BASE_RDF + skill_name)

            data[label] = {
                "uri": subject_uri,
                "description": description,
                "link": DISPLAY_URL + skill_name,
                "subskills": [], #haridus:osaOskus -> koosneb
                "prerequisites": [], #haridus:seotudOskus -> eeldus
                "competency": [], #haridus:eeldab -> õpiväljund
                "esco_link": str(g_rdf.value(subject_uri, ESCO_LINK, default="")),
                "esco_vaste": str(g_rdf.value(subject_uri, ESCO_VASTE, default="")),
                "osk_reg_kood": str(g_rdf.value(subject_uri, OSK_REG_KOOD, default="")),
                "skill_verb": str(g_rdf.value(subject_uri, VERB, default=""))
            }
            depths[label] = depth

            # 1. Leia osad, millest see oskus koosneb (alla suund)
            for o in g_rdf.objects(subject=subject_uri, predicate=OSAOSKUS):
                subskill_uri = str(o)
                subskill_name = uri_to_skill_name(subskill_uri)
                subskill_label = uri_to_label(subskill_uri)

                if subskill_label not in data[label]["subskills"]:
                    data[label]["subskills"].append(subskill_label)

                loader(subskill_name, depth + 1)

            # 2. Leia oskused, mis koosnevad sellest (üles suund)
            for s in g_rdf.subjects(predicate=OSAOSKUS, object=subject_uri):
                parent_skill_name = uri_to_skill_name(str(s))
                parent_label = uri_to_label(str(s))

                if parent_label not in data:
                    loader(parent_skill_name, depth + 1)

            # 3. Leia õpiväljundid (prerequisites) (alla suund)
            for o in g_rdf.objects(subject=subject_uri, predicate=SEOTUD_OSKUS):
                prereq_uri = str(o)
                prereq_name = uri_to_skill_name(prereq_uri)
                prereq_label = uri_to_label(prereq_uri)

                if prereq_label not in data[label]["prerequisites"]:
                    data[label]["prerequisites"].append(prereq_label)

                loader(prereq_name, depth + 1)

            # 4. Leia õpiväljundid (prerequisites) (üles suund)
            for s in g_rdf.subjects(predicate=SEOTUD_OSKUS, object=subject_uri):
                parent_skill_name = uri_to_skill_name(str(s))
                parent_label = uri_to_label(str(s))

                if parent_label not in data:
                    loader(parent_skill_name, depth + 1)

            # 5. Leia seotud oskused (related)
            for o in g_rdf.objects(subject=subject_uri, predicate=EDU.eeldab):
                related_uri = str(o)
                related_name = uri_to_skill_name(related_uri)
                related_label = uri_to_label(related_uri)

                if related_label not in data[label]["competency"]:
                    data[label]["competency"].append(related_label)

                loader(related_name, depth + 1)

            # 5. Leia eeldused (prerequisites) (üles suund)
            for s in g_rdf.subjects(predicate=EDU.eeldab, object=subject_uri):
                parent_skill_name = uri_to_skill_name(str(s))
                parent_label = uri_to_label(str(s))

                if parent_label not in data:
                    loader(parent_skill_name, depth + 1)

        except Exception as e:
            print(f"Error loading RDF for {skill_name}: {e}")

    # Esmane rekursioon
    for skill in skill_list:
        loader(skill)

    # Lisa veel töödlemata oskused otse
    for skill in skill_list:
        label = uri_to_label(skill)
        if label not in data:
            try:
                loader(skill)
            except Exception as e:
                print(f"Secondary load failed for {skill}: {e}")

    print(f"✅ Andmestikus olevad oskused: {list(data.keys())[:10]}")

    if "Probleemilahendus" not in data:
        print("❌ Probleemilahendus puudub data-s!")

    return data, depths

def build_interactive_graph(data, depths, filename="skill_graph.html"):
    """
    Builds and saves an interactive skill graph as an HTML file.
    """
    from pyvis.network import Network
    net = Network(height="100vh", width="100%", directed=True)
    _set_network_options(net)
    _add_nodes(net, data, depths)
    _add_edges(net, data)
    net.write_html(filename)
    _inject_html_controls(filename, depths)

def _set_network_options(net):
    """
       Applies visual and interactive configuration options to the Pyvis network graph.

       The settings define node shape, font, border and colors, edge styling, physics layout, and user interactions
       such as zoom, hover tooltips, and navigation buttons.
       """
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
    """
    Adds all skill nodes to the Pyvis network graph with appropriate styling and metadata.

    Each node is styled with a dynamic size based on number of subskills.
    Tooltip and clickable link are added to provide interactive metadata in the graph.
    """
    for label, info in data.items():
        level = depths.get(label, 0)
        size = 10 + len(info["subskills"]) * 1.5

        # Määra värv sõltuvalt seose tüübist
        if info["prerequisites"]:
            color = "#a1c9f1"  # hele sinine - eelduseks
        elif info["related"]:
            color = "#f4b183"  # oranžikas - seotud oskus
        elif info["related_general"]:
            color = "#d9d9d9"  # hallikas - üldine seotud
        elif info["parts"]:
            color = "#bf98e6"  # hallikas - üldine seotud
        else:
            color = "#b7e1cd"  # rohekas - lihtsalt oskus

        net.add_node(
            label,
            label=label,
            title=f"Skill: {label}\nDescription: {info['description']}\nClick me!",
            shape="dot",
            size=size,
            level=level,
            link=info["link"],
            color=color
        )

def _add_edges(net, data):
    """
      Adds directed edges (links) between skill nodes in the Pyvis network graph.

      For every subskill relationship, a directed edge is created from the subskill to the parent skill.
      Duplicate edges are avoided using a set.
      """
    added_edges = set()
    for label, info in data.items():
        edge_types = [
            ("subskills", "#2b7bba"),  # blue
            ("prerequisites", "#58a55c"),  # green
            ("related", "#f29e4c"),  # orange
            ("related_general", "#999999"),  # gray
            ("parts", "#bf98e6")  # lilla – osaoskused
        ]

        for key, color in edge_types:
            for target in info.get(key, []):
                if target in data:
                    edge = (target, label, color)
                    if edge not in added_edges:
                        net.add_edge(source=target, to=label, color=color)
                        added_edges.add(edge)

def _inject_html_controls(filename, depths):
    """
    Injects search and level-based filtering controls into the generated HTML skill graph.

    This function modifies the existing HTML file by:
    - Adding a search input field to filter nodes by label.
    - Adding dynamic checkbox filters for each depth level (Level 0, 1, 2, ...).
    - Appending JavaScript that implements filtering and node interaction logic.
    """
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
    <div id=\"controls\">
      <input type=\"text\" id=\"searchBox\" placeholder=\"Search skill...\" oninput=\"searchNode()\" />
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
    """
    Exports the skill graph as a GraphML file using NetworkX.

    This function creates a directed graph where each skill is a node,
    and edges represent subskill relationships. The resulting graph is saved
    in the GraphML format, which is useful for further analysis or visualization
    with graph tools like Gephi or Cytoscape.
    """
    g = nx.DiGraph()
    for label, info in data.items():
        g.add_node(label, description=info["description"], link=info["link"])
        for sub in info["subskills"]:
            g.add_edge(sub, label)
    nx.write_graphml(g, filename)
    print(f"GraphML exported: {filename}")

if __name__ == "__main__":
    skills = get_all_skills(SKILLS_URL)
    parsed_data, depths = parse_all_skills_recursive(skills)
    build_interactive_graph(parsed_data, depths)
    if EXPORT_GRAPHML:
        export_graphml(parsed_data)
