import json, os
from flask import Blueprint, render_template, request, jsonify
import asyncio

from logic import graph_utils
from logic.graph_utils import parse_all_data_async, get_all_data, SKILLS_URL, COMPETENCIES_URL, TEGEVUSNAITAJAD_URL, KNOBITID_URL, OPIVALJUNDID_URL, normalize_key

main_bp = Blueprint("main", __name__)

GRAPH_CACHE_PATH = "data/graph_data.json"  # tee, kuhu salvestame graafi
os.makedirs("data", exist_ok=True)  # loo kaust, kui seda pole

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/graph")
def get_graph_data():
    skill = request.args.get("skill", "").strip()

    if not skill and os.path.exists(GRAPH_CACHE_PATH):
        with open(GRAPH_CACHE_PATH, "r", encoding="utf-8") as f:
            print("✅ Kasutatakse olemasolevat JSON cache'i.")
            return jsonify(json.load(f))

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
            opivaljundid = get_all_data(OPIVALJUNDID_URL)

            data_list = skills + competencies + tegevusnaitajad + knobitid + opivaljundid

            skills_set = {normalize_key(s) for s in skills}
            competencies_set = {normalize_key(c) for c in competencies}
            tn_set = {normalize_key(t) for t in tegevusnaitajad}
            knobit_set = {normalize_key(k) for k in knobitid}
            opivaljund_set = {normalize_key(o) for o in opivaljundid}

        else:
            data_list = [normalize_key(skill)]
            skills_set = set()
            competencies_set = set()
            tn_set = set()
            knobit_set = set()
            opivaljund_set = set()

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
                color = "#ff7f11"  # erkoranž
                node_type = "kompetents"
            elif key in tn_set:
                node_label = f"Tegevusnäitaja: {label}"
                color = "#00b894"  # erkroheline
                node_type = "tegevusnaitaja"
            elif key in knobit_set:
                node_label = f"Knobit: {label}"
                color = "#6c5ce7"  # lilla-sinine
                node_type = "knobit"
            elif key in skills_set:
                node_label = f"Oskus: {label}"
                color = "#0984e3"  # eredalt sinine
                node_type = "oskus"
            elif key in opivaljund_set:
                node_label = f"Õpiväljund: {label}"
                color = "#e1b12c"  # kuldkollane
                node_type = "opivaljund"
            else:
                node_label = f"Tundmatu: {label}"
                color = "#636e72"  # neutraalne hall
                node_type = "muu"

            nodes.append({
                "id": key,
                "label": node_label,
                "description": info.get("description", ""),
                "level": level,
                "size": 25 + len(info.get("subskills", [])) * 1.5,
                "link": info.get("link", ""),
                "esco_link": info.get("esco_link", ""),
                "esco_vaste": info.get("esco_vaste", ""),
                "osk_reg_kood": info.get("osk_reg_kood", ""),
                "skill_verb": info.get("skill_verb", ""),
                "color": color,
                "relevant_occupations": info.get("relevant_occupations", []),
                "type": node_type,
                "klass": info.get("klass", ""),
                "kooliaste": info.get("kooliaste", ""),
                "seotud_oppeaine": info.get("seotud_oppeaine", ""),
                "seotud_teema": info.get("seotud_teema", ""),
            })

            # Edges (NB! targetid normaliseeri sama moodi nagu key)
            for sub in info.get("subskills", []):
                if sub in data:  # ainult kui target on data-s olemas
                    edges.append({
                        "from": sub,
                        "to": key,
                        "color": "#ff3b30",
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
                        "color": "#007aff",
                        "label": "eeldab"
                    })

            # Tegevusnäitajad
            for tn in info.get("tegevusnaitajad", []):
                if tn in data:
                    edges.append({
                        "from": tn,
                        "to": key,
                        "color": "#34c759",
                        "label": "sisaldab Tn"
                    })

            # Knobitid
            for kn in info.get("knobitid", []):
                if kn in data:
                    edges.append({
                        "from": kn,
                        "to": key,
                        "color": "#af52de",
                        "label": "sisaldab knobitit"
                    })

            for tn_req in info.get("tn_eeldab", []):
                if tn_req in data:
                    edges.append({
                        "from": tn_req,
                        "to": key,
                        "color": "#5856d6",
                        "label": "Tn eeldab"
                    })

            # Õpiväljund sisaldab knobitit
            for ov_kn in info.get("ov_knobitid", []):
                if ov_kn in data:
                    edges.append({
                        "from": ov_kn,
                        "to": key,
                        "color": "#ffd60a",
                        "label": "sisaldab knobitit (OV)"
                    })

            # Õpiväljund eeldab teist õpiväljundit
            for ov_pre in info.get("eeldab", []):
                if ov_pre in data:
                    edges.append({
                        "from": ov_pre,
                        "to": key,
                        "color": "#ff9500",
                        "label": "eeldab (OV)"
                    })

        result = {"nodes": nodes, "edges": edges}

        # Kui laeti kogu graaf, salvesta cache'i
        if not skill:
            with open(GRAPH_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"💾 Salvestati graaf JSON cache'i: {GRAPH_CACHE_PATH}")

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500