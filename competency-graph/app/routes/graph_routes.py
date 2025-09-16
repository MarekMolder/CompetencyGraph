from flask import Blueprint, render_template, request, jsonify
import asyncio

from logic import graph_utils
from logic.graph_utils import parse_all_data_async, get_all_data, SKILLS_URL, COMPETENCIES_URL, TEGEVUSNAITAJAD_URL, KNOBITID_URL, normalize_key

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/graph")
def get_graph_data():
    skill = request.args.get("skill", "").strip()
    limit_recursion = request.args.get("limit_recursion", "false").lower() == "true"
    max_depth = int(request.args.get("max_depth", 9999999))

    graph_utils.LIMIT_RECURSION = limit_recursion
    graph_utils.MAX_DEPTH = max_depth

    try:
        if not skill:
            skills = get_all_data(SKILLS_URL)
            competencies = get_all_data(COMPETENCIES_URL)
            tegevusnaitajad = get_all_data(TEGEVUSNAITAJAD_URL)
            knobitid = get_all_data(KNOBITID_URL)

            data_list = skills + competencies + tegevusnaitajad + knobitid
            skills_set = {normalize_key(s) for s in skills}
            competencies_set = {normalize_key(c) for c in competencies}
            tn_set = {normalize_key(t) for t in tegevusnaitajad}
            knobit_set = {normalize_key(k) for k in knobitid}
        else:
            data_list = [normalize_key(skill)]
            skills_set = set()
            competencies_set = set()
            tn_set = set()
            knobit_set = set()

        data, depths = asyncio.run(parse_all_data_async(data_list))

        if not data or all(
            len(info.get("subskills", [])) == 0 and
            len(info.get("prerequisites", [])) == 0 and
            len(info.get("tegevusnaitajad", [])) == 0
            for info in data.values()
        ):
            return jsonify({"error": "Oskust/kompetentsi ei leitud"}), 404

        nodes, edges = [], []

        for key, info in data.items():
            label = info.get("label", key.replace("_", " "))
            level = depths.get(key, -1)

            if key in competencies_set:
                node_label = f"Kompetents: {label}"
                color = "#FFA500"  # oranž
                node_type = "kompetents"
            elif key in tn_set:
                node_label = f"Tegevusnäitaja: {label}"
                color = "#27ae60"  # roheline
                node_type = "tegevusnaitaja"
            elif key in knobit_set:
                node_label = f"Knobit: {label}"
                color = "#9b59b6"  # lilla
                node_type = "knobit"
            elif key in skills_set:
                node_label = f"Oskus: {label}"
                color = "#a1c9f1"  # sinine
                node_type = "oskus"
            else:
                node_label = f"Tundmatu: {label}"
                color = "#7f8c8d"  # hall
                node_type = "muu"

            nodes.append({
                "id": key,
                "label": node_label,
                "description": info.get("description", ""),
                "level": level,
                "size": 10 + len(info.get("subskills", [])) * 1.5,
                "link": info.get("link", ""),
                "esco_link": info.get("esco_link", ""),
                "esco_vaste": info.get("esco_vaste", ""),
                "osk_reg_kood": info.get("osk_reg_kood", ""),
                "skill_verb": info.get("skill_verb", ""),
                "color": color,
                "relevant_occupations": info.get("relevant_occupations", []),
                "type": node_type,
            })

            # Edges (NB! targetid normaliseeri sama moodi nagu key)
            for sub in info.get("subskills", []):
                if sub in data:  # ainult kui target on data-s olemas
                    edges.append({
                        "from": sub,
                        "to": key,
                        "color": "#e74c3c",
                        "label": "koosneb",
                        "dashes": True,
                        "arrows": {"to": {"enabled": True, "type": "vee"}}
                    })

            # Prerequisites
            for pre in info.get("prerequisites", []):
                if pre in data:
                    edges.append({
                        "from": pre,
                        "to": key,
                        "color": "#2980b9",
                        "label": "eeldab"
                    })

            # Tegevusnäitajad
            for tn in info.get("tegevusnaitajad", []):
                if tn in data:
                    edges.append({
                        "from": tn,
                        "to": key,
                        "color": "#27ae60",
                        "label": "sisaldab Tn"
                    })

            # Knobitid
            for kn in info.get("knobitid", []):
                if kn in data:
                    edges.append({
                        "from": kn,
                        "to": key,
                        "color": "#9b59b6",
                        "label": "sisaldab knobitit"
                    })

            for tn_req in info.get("tn_eeldab", []):
                if tn_req in data:
                    edges.append({
                        "from": tn_req,
                        "to": key,
                        "color": "#2980b9",
                        "label": "Tn eeldab"
                    })

        return jsonify({"nodes": nodes, "edges": edges})

    except Exception as e:
        return jsonify({"error": str(e)}), 500