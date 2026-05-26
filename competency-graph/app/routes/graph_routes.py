import json, os
from flask import Blueprint, render_template, request, jsonify
import asyncio
from flask import session
import threading
import importlib


from logic import graph_utils
from logic.graph_utils import (parse_all_data_async, get_all_data,
    SKILLS_URL, COMPETENCIES_URL, TEGEVUSNAITAJAD_URL, KNOBITID_URL,
    OPIVALJUNDID_URL, AMETIKOMPETENTSIPROFIIL_URL, OPPEAINE_TASEMEOPE_URL,
    VALDKONNA_KOMPETENTSIPROFIIL_URL, OPPEKAVA_URL, normalize_key,
    load_relation_config, CACHE)


_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
os.makedirs(_DATA_DIR, exist_ok=True)

SYNC_STATUS_PATH = os.path.join(_DATA_DIR, "sync_status.json")
GRAPH_CACHE_PATH = os.path.join(_DATA_DIR, "graph_data.json")

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    return render_template("index.html", logged_in=session.get("logged_in"))

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
            ametikompetentsid = get_all_data(AMETIKOMPETENTSIPROFIIL_URL)
            oppeained = get_all_data(OPPEAINE_TASEMEOPE_URL)
            valdkonna_kompetentsid = get_all_data(VALDKONNA_KOMPETENTSIPROFIIL_URL)
            oppekavad = get_all_data(OPPEKAVA_URL)

            data_list = skills + competencies + tegevusnaitajad + knobitid + opivaljundid + ametikompetentsid + oppeained + valdkonna_kompetentsid + oppekavad

            skills_set = {normalize_key(s) for s in skills}
            competencies_set = {normalize_key(c) for c in competencies}
            tn_set = {normalize_key(t) for t in tegevusnaitajad}
            knobit_set = {normalize_key(k) for k in knobitid}
            opivaljund_set = {normalize_key(o) for o in opivaljundid}
            ametikompetents_set = {normalize_key(a) for a in ametikompetentsid}
            oppeaine_set = {normalize_key(o) for o in oppeained}
            valdkonna_komp_set = {normalize_key(v) for v in valdkonna_kompetentsid}
            oppekava_set = {normalize_key(o) for o in oppekavad}

        else:
            data_list = [normalize_key(skill)]
            skills_set = set()
            competencies_set = set()
            tn_set = set()
            knobit_set = set()
            opivaljund_set = set()
            oppekava_set = set()

        data, depths = asyncio.run(parse_all_data_async(data_list))

        if not data:
            return jsonify({"error": "Andmeid ei leitud"}), 404

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
            elif key in ametikompetents_set:
                node_label = f"AmetiKomp: {label}"
                color = "#e84393"  # roosa
                node_type = "ametikompetents"
            elif key in oppeaine_set:
                node_label = f"Õppeaine: {label}"
                color = "#00cec9"  # türkiis
                node_type = "oppeaine"
            elif key in valdkonna_komp_set:
                node_label = f"ValdkonnaKomp: {label}"
                color = "#2d6a4f"  # tumeroheline
                node_type = "valdkonnakomp"
            elif key in oppekava_set:
                node_label = f"Õppekava: {label}"
                color = "#d63031"  # punane
                node_type = "oppekava"
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
                "knobiti_liik": info.get("knobiti_liik", ""),
                "oppeaine_eesmargid": info.get("oppeaine_eesmargid", ""),
                "oppeaine_maht_eap": info.get("oppeaine_maht_eap", ""),
                "oppeasutus": info.get("oppeasutus", ""),
                "course_code": info.get("course_code", ""),
                "oppekava_nimetus_en": info.get("oppekava_nimetus_en", ""),
                "oppekava_identifier": info.get("oppekava_identifier", ""),
                "oppekava_credits": info.get("oppekava_credits", ""),
                "oppekava_provider": info.get("oppekava_provider", ""),
            })

            importlib.reload(graph_utils)
            relation_config = load_relation_config()

            for rel_name, rel in relation_config.items():
                label = rel.get("label", rel_name)
                color = rel.get("color", "#999")
                direction = rel.get("direction", "child-to-parent")

                for tgt in info.get(rel_name, []):
                    if tgt not in data:
                        continue

                    if direction == "child-to-parent":
                        edge_from = tgt
                        edge_to = key
                    else:  # parent-to-child
                        edge_from = key
                        edge_to = tgt

                    edge_obj = {
                        "from": edge_from,
                        "to": edge_to,
                        "label": label,
                        "color": color
                    }

                    # Lisa dashes + arrows ainult KOOSNEB (OSAOSKUS)
                    if rel_name == "OSAOSKUS":
                        edge_obj["dashes"] = True
                        edge_obj["arrows"] = {"to": {"enabled": True, "type": "vee"}}

                    edges.append(edge_obj)

        result = {"nodes": nodes, "edges": edges}

        # Kui laeti kogu graaf, salvesta cache'i
        if not skill:
            with open(GRAPH_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"💾 Salvestati graaf JSON cache'i: {GRAPH_CACHE_PATH}")

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main_bp.route("/sync_graph", methods=["POST"])
def sync_graph():
    from flask import session, current_app
    import time

    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    def background_sync():
        try:
            # Alusta progressifailist
            with open(SYNC_STATUS_PATH, "w", encoding="utf-8") as f:
                json.dump({"progress": 0, "status": "🔄 Käivitan graafi uuenduse..."}, f)

            # 1️⃣ Kustuta vana cache (nii JSON kui RDF diskcache)
            if os.path.exists(GRAPH_CACHE_PATH):
                os.remove(GRAPH_CACHE_PATH)
            CACHE.clear()
            with open(SYNC_STATUS_PATH, "w", encoding="utf-8") as f:
                json.dump({"progress": 5, "status": "🗑️ Vana cache kustutatud..."}, f)

            # 2️⃣ Lae RDF andmete kategooriad
            urls = [
                SKILLS_URL,
                COMPETENCIES_URL,
                TEGEVUSNAITAJAD_URL,
                KNOBITID_URL,
                OPIVALJUNDID_URL,
                AMETIKOMPETENTSIPROFIIL_URL,
                OPPEAINE_TASEMEOPE_URL,
                VALDKONNA_KOMPETENTSIPROFIIL_URL,
                OPPEKAVA_URL,
            ]
            all_data = []
            total = len(urls)
            for i, url in enumerate(urls, 1):
                name = url.split(":")[-1]
                all_data += get_all_data(url)
                with open(SYNC_STATUS_PATH, "w", encoding="utf-8") as f:
                    json.dump({
                        "progress": int(i / total * 10),
                        "status": f"📂 Laen kategooriat: {name} ({i}/{total})..."
                    }, f)

            # 3️⃣ Lae RDF andmed (suured RDF failid)
            with open(SYNC_STATUS_PATH, "w", encoding="utf-8") as f:
                json.dump({"progress": 20, "status": "🧠 Laen RDF andmeid ja parsin (see võib võtta aega)..."}, f)

            # RDF laadimine ja parsimine
            data, depths = asyncio.run(parse_all_data_async(all_data))

            # 4️⃣ Ehita graaf täpselt nagu /graph teeb
            with open(SYNC_STATUS_PATH, "w", encoding="utf-8") as f:
                json.dump({"progress": 60, "status": "🔗 Koostan graafi sõlmi ja seoseid..."}, f)

            # Ehita kõik noded ja edges (täpselt sama loogika kui get_graph_data-s)
            skills = get_all_data(SKILLS_URL)
            competencies = get_all_data(COMPETENCIES_URL)
            tegevusnaitajad = get_all_data(TEGEVUSNAITAJAD_URL)
            knobitid = get_all_data(KNOBITID_URL)
            opivaljundid = get_all_data(OPIVALJUNDID_URL)
            ametikompetentsid = get_all_data(AMETIKOMPETENTSIPROFIIL_URL)
            oppeained = get_all_data(OPPEAINE_TASEMEOPE_URL)
            valdkonna_kompetentsid = get_all_data(VALDKONNA_KOMPETENTSIPROFIIL_URL)
            oppekavad = get_all_data(OPPEKAVA_URL)

            skills_set = {normalize_key(s) for s in skills}
            competencies_set = {normalize_key(c) for c in competencies}
            tn_set = {normalize_key(t) for t in tegevusnaitajad}
            knobit_set = {normalize_key(k) for k in knobitid}
            opivaljund_set = {normalize_key(o) for o in opivaljundid}
            ametikompetents_set = {normalize_key(a) for a in ametikompetentsid}
            oppeaine_set = {normalize_key(o) for o in oppeained}
            valdkonna_komp_set = {normalize_key(v) for v in valdkonna_kompetentsid}
            oppekava_set = {normalize_key(o) for o in oppekavad}

            nodes, edges = [], []

            for key, info in data.items():
                label = info.get("label", key.replace("_", " "))
                level = depths.get(key, -1)

                if key in competencies_set:
                    node_label = f"Kompetents: {label}"
                    color = "#ff7f11"
                    node_type = "kompetents"
                elif key in tn_set:
                    node_label = f"Tegevusnäitaja: {label}"
                    color = "#00b894"
                    node_type = "tegevusnaitaja"
                elif key in knobit_set:
                    node_label = f"Knobit: {label}"
                    color = "#6c5ce7"
                    node_type = "knobit"
                elif key in skills_set:
                    node_label = f"Oskus: {label}"
                    color = "#0984e3"
                    node_type = "oskus"
                elif key in opivaljund_set:
                    node_label = f"Õpiväljund: {label}"
                    color = "#e1b12c"
                    node_type = "opivaljund"
                elif key in ametikompetents_set:
                    node_label = f"AmetiKomp: {label}"
                    color = "#e84393"
                    node_type = "ametikompetents"
                elif key in oppeaine_set:
                    node_label = f"Õppeaine: {label}"
                    color = "#00cec9"
                    node_type = "oppeaine"
                elif key in valdkonna_komp_set:
                    node_label = f"ValdkonnaKomp: {label}"
                    color = "#2d6a4f"
                    node_type = "valdkonnakomp"
                elif key in oppekava_set:
                    node_label = f"Õppekava: {label}"
                    color = "#d63031"
                    node_type = "oppekava"
                else:
                    node_label = f"Tundmatu: {label}"
                    color = "#636e72"
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
                    "knobiti_liik": info.get("knobiti_liik", ""),
                    "oppeaine_eesmargid": info.get("oppeaine_eesmargid", ""),
                    "oppeaine_maht_eap": info.get("oppeaine_maht_eap", ""),
                    "oppeasutus": info.get("oppeasutus", ""),
                    "course_code": info.get("course_code", ""),
                    "oppekava_nimetus_en": info.get("oppekava_nimetus_en", ""),
                    "oppekava_identifier": info.get("oppekava_identifier", ""),
                    "oppekava_credits": info.get("oppekava_credits", ""),
                    "oppekava_provider": info.get("oppekava_provider", ""),
                })

                importlib.reload(graph_utils)
                relation_config = load_relation_config()

                # Lisa kõik seosed configi alusel
                for rel_name, rel in relation_config.items():
                    rel_label = rel.get("label", rel_name)
                    rel_color = rel.get("color", "#999")
                    rel_direction = rel.get("direction", "child-to-parent")

                    targets = info.get(rel_name, [])
                    if not targets:
                        continue

                    for tgt in targets:
                        if tgt not in data:
                            continue

                        if rel_direction == "child-to-parent":
                            edge_from = tgt
                            edge_to = key
                        else:
                            edge_from = key
                            edge_to = tgt

                        edge_obj = {
                            "from": edge_from,
                            "to": edge_to,
                            "label": rel_label,
                            "color": rel_color
                        }

                        # Ainult KOOSNEB (OSAOSKUS) saab dashes + arrows
                        if rel_name == "OSAOSKUS":
                            edge_obj["dashes"] = True
                            edge_obj["arrows"] = {"to": {"enabled": True, "type": "vee"}}

                        edges.append(edge_obj)

            # 5️⃣ Salvesta uus graaf
            with open(SYNC_STATUS_PATH, "w", encoding="utf-8") as f:
                json.dump({"progress": 90, "status": "💾 Salvestan uut graafi..."}, f)

            result = {"nodes": nodes, "edges": edges}
            with open(GRAPH_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            with open(SYNC_STATUS_PATH, "w", encoding="utf-8") as f:
                json.dump({"progress": 100, "status": "✅ Uus graaf edukalt loodud!"}, f)

            print(f"💾 Uus graaf salvestatud: {GRAPH_CACHE_PATH}")

        except Exception as e:
            with open(SYNC_STATUS_PATH, "w", encoding="utf-8") as f:
                json.dump({"progress": -1, "status": f"❌ Viga: {str(e)}"}, f)

    # Käivita eraldi threadis, et mitte UI-d blokeerida
    threading.Thread(target=background_sync, daemon=True).start()
    return jsonify({"started": True})

@main_bp.route("/sync_progress")
def sync_progress():
    if os.path.exists(SYNC_STATUS_PATH):
        with open(SYNC_STATUS_PATH, "r", encoding="utf-8") as f:
            try:
                return jsonify(json.load(f))
            except Exception:
                return jsonify({"progress": 0, "status": "❌ Vigane progressifail"})
    else:
        return jsonify({"progress": 0, "status": "⏳ Ootel..."})

@main_bp.route("/admin/add_relation", methods=["POST"])
def add_relation():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    if not data:
        return jsonify({"error": "Invalid payload"}), 400

    key = data.get("key")
    predicate = data.get("predicate")
    label = data.get("label")
    color = data.get("color")
    direction = data.get("direction")

    if not key or not predicate or not label:
        return jsonify({"error": "Missing required fields"}), 400

    config_path = "data/relation_config.json"

    # loe config
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}

    # lisa uus key
    cfg[key] = {
        "predicate": predicate,
        "label": label,
        "color": color,
        "direction": direction
    }

    # kirjuta tagasi
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    return jsonify({"success": True})


