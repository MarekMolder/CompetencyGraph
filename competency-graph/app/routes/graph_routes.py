from flask import Blueprint, render_template, request, jsonify
import asyncio

from logic import graph_utils
from logic.graph_utils import parse_all_skills_async, get_all_skills, SKILLS_URL

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    """Render the main index page."""
    return render_template("index.html")

@main_bp.route("/graph")
def get_graph_data():
    """
    Endpoint to generate graph data based on a given skill.

    Status Codes:
        200: Successfully returned graph data.
        404: Skill not found or has no subskills.
        500: Internal server error during processing.
    """
    skill = request.args.get("skill", "").strip()
    limit_recursion = request.args.get("limit_recursion", "false").lower() == "true"
    max_depth = int(request.args.get("max_depth", 9999999))

    # Dünaamilised lipud enne parse’i
    graph_utils.LIMIT_RECURSION = limit_recursion
    graph_utils.MAX_DEPTH = max_depth

    try:
        if not skill:
            skill_list = get_all_skills(SKILLS_URL)
        else:
            skill_list = [skill.replace(" ", "_")]

        # ⬇️ ASÜNKROONNE PARSING KÄIMA
        data, depths = asyncio.run(parse_all_skills_async(skill_list))

        if not data or all(
            len(info.get("subskills", [])) == 0 and
            len(info.get("prerequisites", [])) == 0 and
            len(info.get("competency", [])) == 0
            for info in data.values()
        ):
            return jsonify({"error": "Oskust ei leitud"}), 404

        nodes = []
        edges = []

        for label, info in data.items():
            level = depths.get(label, -1)
            nodes.append({
                "id": label,
                "label": label,
                "description": info.get("description", ""),
                "level": level,
                "size": 10 + len(info.get("subskills", [])) * 1.5,
                "link": info.get("link", ""),
                "esco_link": info.get("esco_link", ""),
                "esco_vaste": info.get("esco_vaste", ""),
                "osk_reg_kood": info.get("osk_reg_kood", ""),
                "skill_verb": info.get("skill_verb", "")
            })

            # Subskills - haridus:osaOskus -> koosneb
            for sub in info.get("subskills", []):
                edges.append({
                    "from": sub,
                    "to": label,
                    "color": "#e74c3c",
                    "label": "koosneb",
                    "dashes": True,
                    "arrows": {"to": {"enabled": True, "type": "vee"}}
                })

            # Prerequisites - #haridus:seotudOskus -> eeldus
            for pre in info.get("prerequisites", []):
                edges.append({
                    "from": pre,
                    "to": label,
                    "color": "#2980b9",
                    "label": "eeldab"
                })

            # Related - #haridus:eeldab -> õpiväljund
            for rel in info.get("competency", []):
                edges.append({
                    "from": rel,
                    "to": label,
                    "color": "#58a55c",
                    "label": "õpiväljund"
                })

        return jsonify({"nodes": nodes, "edges": edges})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
