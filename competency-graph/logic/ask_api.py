import asyncio
from collections import deque
from typing import Optional
from urllib.parse import quote

import aiohttp
from aiolimiter import AsyncLimiter

LIMIT_RECURSION: bool = False
MAX_DEPTH: int = 999_999_999

BASE_URL = "https://oppekava.edu.ee/w/api.php"
MAX_CONCURRENCY = 8
REQS_PER_SEC = 8
HTTP_TIMEOUT = 30
RETRIES = 4
PAGE_SIZE = 500
# Category-level retries (on top of per-HTTP-request RETRIES). A transient
# upstream error during the parallel burst must not silently drop a whole
# category (this intermittently lost the small "oppekava" category).
CATEGORY_RETRIES = 3

_semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
_rate = AsyncLimiter(REQS_PER_SEC, time_period=1)

# Category suffix (as appears in URLs like .../Kategooria:Haridus:Oskus)
# -> (smw_category_name, node_type)
CATEGORY_URL_TO_NAME = {
    "Haridus:Oskus": ("Haridus:Oskus", "oskus"),
    "Haridus:Kompetents": ("Haridus:Kompetents", "kompetents"),
    "Haridus:Tegevusnaitaja": ("Haridus:Tegevusnaitaja", "tegevusnaitaja"),
    "Haridus:Knobit": ("Haridus:Knobit", "knobit"),
    "Haridus:Opivaljund": ("Haridus:Opivaljund", "opivaljund"),
    "Haridus:AmetiKompetentsiProfiil": ("Haridus:AmetiKompetentsiProfiil", "ametikompetents"),
    "Haridus:OppeaineTasemeOpe": ("Haridus:OppeaineTasemeOpe", "oppeaine"),
    "Haridus:ValdkonnaKompetentsiProfiil": ("Haridus:ValdkonnaKompetentsiProfiil", "valdkonnakomp"),
    "Haridus:Oppekava": ("Haridus:Oppekava", "oppekava"),
}

# Printout attributes to request per node_type. Names must include namespace.
ATTRIBUTES_BY_TYPE = {
    "oskus": [
        "Schema:description",
        "Haridus:esco_link", "Haridus:esco_vaste",
        "Haridus:osk_reg_kood", "Haridus:verb",
        "Haridus:osaOskus", "Haridus:eeldusOskus",
        "Schema:relevantOccupation",
    ],
    "kompetents": [
        "Schema:description",
        "Haridus:KompSisaldabTn", "Haridus:KompEeldabOskreg",
    ],
    "tegevusnaitaja": [
        "Schema:description",
        "Haridus:TnSisaldabKnobitit", "Haridus:TnEeldab", "Haridus:TnMoodabOv",
    ],
    "knobit": [
        "Schema:description",
        "Haridus:knobiti_liik",
        "Haridus:KnobitEeldab", "Haridus:KnobitSisaldab",
    ],
    "opivaljund": [
        "Schema:description",
        "Haridus:klass", "Haridus:kooliaste",
        "Haridus:seotud_oppeaine", "Haridus:seotud_teema",
        "Haridus:OvSisaldabKnobitit",
        # Schema.edu.ee namespace is registered as "Haridus" prefix in SMW,
        # so https://schema.edu.ee/eeldab is queried as Haridus:eeldab.
        "Haridus:eeldab",
        # SEOTUD_OPPEKAVA: property lives on opivaljund pages pointing to oppekava
        "Haridus:seotudOppekava",
    ],
    "ametikompetents": [
        "Schema:description",
        "Haridus:AmKoPrKoosnebKomp",
    ],
    "oppeaine": [
        "Schema:description",
        "Haridus:oppeaine_eesmargid", "Haridus:oppeaine_maht_eap",
        "Haridus:oppeasutus", "Haridus:course_code",
        "Haridus:AineEeldbTasemeOpe", "Haridus:OpTaOpSisaldabOpivaljund",
        "Haridus:seotudOppekava",
    ],
    "valdkonnakomp": [
        "Schema:description",
        "Haridus:AmKoPrKoosnebKomp",
    ],
    "oppekava": [
        "Schema:description",
        "Haridus:oppekava_nimetus_en", "Haridus:oppekava_identifier",
        "Haridus:oppekava_credits", "Haridus:oppekava_provider",
        "Haridus:OppekavaOppvaljund",
    ],
}

# Map normalized printout short-key -> field name on data[key].
# Normalization: strip namespace, replace spaces with underscores.
# (SMW returns "Haridus:esco link" not "Haridus:esco_link".)
SCALAR_PRINTOUT_TO_FIELD = {
    "esco_link": "esco_link",
    "esco_vaste": "esco_vaste",
    "osk_reg_kood": "osk_reg_kood",
    "verb": "skill_verb",
    "klass": "klass",
    "kooliaste": "kooliaste",
    "seotud_oppeaine": "seotud_oppeaine",
    "seotud_teema": "seotud_teema",
    "knobiti_liik": "knobiti_liik",
    "oppeaine_eesmargid": "oppeaine_eesmargid",
    "oppeaine_maht_eap": "oppeaine_maht_eap",
    "oppeasutus": "oppeasutus",
    "course_code": "course_code",
    "oppekava_nimetus_en": "oppekava_nimetus_en",
    "oppekava_identifier": "oppekava_identifier",
    "oppekava_credits": "oppekava_credits",
    "oppekava_provider": "oppekava_provider",
}

# Map normalized printout short-key -> relation_name in relation_config.json.
# Edge predicates are PascalCase / camelCase and come back unchanged from the API,
# EXCEPT the default-namespace "eeldab" which the API capitalizes to "Eeldab".
# Lookup is done case-insensitively in the parser.
EDGE_PRINTOUT_TO_RELATION = {
    "osaoskus": "OSAOSKUS",
    "eeldusoskus": "EELDUS_OSKUS",
    "kompsisaldabtn": "KOMP_SISALDAB_TN",
    "kompeeldaboskreg": "KOMP_EELDAB_OSKREG",
    "tnsisaldabknobitit": "TN_SISALDAB_KNOBITIT",
    "tneeldab": "TN_EELDAB",
    "tnmoodabov": "TN_MOODAB_OV",
    "knobiteeldab": "KNOBIT_EELDAB",
    "knobitsisaldab": "KNOBIT_SISALDAB",
    "ovsisaldabknobitit": "OV_SISALDAB_KNOBITIT",
    "amkoprkoosnebkomp": "AMKOPR_KOOSNEB_KOMP",
    "aineeeldbtasemeope": "AINE_EELDAB_TASEMEOPE",
    "optaopsisaldabopivaljund": "OPTAOP_SISALDAB_OV",
    "oppekavaoppvaljund": "OPPEKAVA_OPPVALJUND",
    "seotudoppekava": "SEOTUD_OPPEKAVA",
    "eeldab": "OV_EELDAB",
}


def _normalize_short_key(short: str) -> str:
    """Normalize an SMW printout short-key for lookup: spaces -> underscores, lower."""
    return short.replace(" ", "_").lower()


def _extract_scalar(value) -> str:
    """Convert a single printout value (string or dict) to a plain string."""
    if isinstance(value, dict):
        return value.get("fulltext") or value.get("fullurl") or ""
    return str(value)


def parse_page_to_node(page_title: str, page_data: dict, node_type: str) -> dict:
    """Build a `data[key]` dict entry from one ask API result page.

    Output shape matches the legacy graph_utils format so graph_routes.py can
    consume it unchanged. Edge lists are populated here; BFS reachability
    filtering happens later in parse_all_data_async.
    """
    printouts = page_data.get("printouts", {}) or {}
    label = page_title.replace("_", " ")

    node = {
        "label": label,
        "uri": "",
        "description": "",
        "link": page_data.get("fullurl", ""),
        "subskills": [],
        "prerequisites": [],
        "competencies": [],
        "tegevusnaitajad": [],
        "knobitid": [],
        "esco_link": "",
        "esco_vaste": "",
        "osk_reg_kood": "",
        "skill_verb": "",
        "klass": "",
        "kooliaste": "",
        "seotud_oppeaine": "",
        "seotud_teema": "",
        "knobiti_liik": "",
        "oppeaine_eesmargid": "",
        "oppeaine_maht_eap": "",
        "oppeasutus": "",
        "course_code": "",
        "oppekava_nimetus_en": "",
        "oppekava_identifier": "",
        "oppekava_credits": "",
        "oppekava_provider": "",
        "relevant_occupations": [],
    }

    # Description (Schema namespace; default empty if missing)
    desc_values = printouts.get("Schema:description") or printouts.get("description") or []
    if desc_values:
        node["description"] = _extract_scalar(desc_values[0])

    # Scalar attributes
    for printout_key, values in printouts.items():
        if not values:
            continue
        short = printout_key.split(":", 1)[1] if ":" in printout_key else printout_key
        norm = _normalize_short_key(short)
        if norm in SCALAR_PRINTOUT_TO_FIELD:
            node[SCALAR_PRINTOUT_TO_FIELD[norm]] = _extract_scalar(values[0])

    # Relevant occupations
    occ_values = printouts.get("Schema:relevantOccupation", []) or []
    for v in occ_values:
        if isinstance(v, dict):
            node["relevant_occupations"].append({
                "uri": v.get("fullurl", ""),
                "label": v.get("fulltext", ""),
            })

    # Edges — append normalized target keys under relation_name
    # Lazy import to avoid circular import with graph_utils (which will re-export
    # this module after Task 11).
    from logic.graph_utils import normalize_key
    for printout_key, values in printouts.items():
        if not values:
            continue
        short = printout_key.split(":", 1)[1] if ":" in printout_key else printout_key
        norm = _normalize_short_key(short)
        if norm not in EDGE_PRINTOUT_TO_RELATION:
            continue
        rel_name = EDGE_PRINTOUT_TO_RELATION[norm]
        node.setdefault(rel_name, [])
        for v in values:
            target_title = v.get("fulltext", "") or v.get("fullurl", "") if isinstance(v, dict) else str(v)
            if not target_title:
                continue
            node[rel_name].append(normalize_key(target_title))

    return node


def _iter_edge_targets(node: dict):
    """Yield all target keys across every relation_name list in a node dict."""
    for rel_name in EDGE_PRINTOUT_TO_RELATION.values():
        for tgt in node.get(rel_name, []) or []:
            yield tgt


def _bfs_filter(
    data: dict,
    seeds: list,
    limit_recursion: bool = False,
    max_depth: int = MAX_DEPTH,
) -> tuple:
    """BFS from seeds through relation edges. Returns (reachable_data, depths)."""
    depths: dict = {}
    queue: deque = deque()

    for s in seeds:
        if s in data and s not in depths:
            depths[s] = 0
            queue.append((s, 0))

    while queue:
        key, depth = queue.popleft()
        if limit_recursion and depth >= max_depth:
            continue
        node = data.get(key, {})
        for tgt in _iter_edge_targets(node):
            if tgt in data and tgt not in depths:
                depths[tgt] = depth + 1
                queue.append((tgt, depth + 1))

    reachable = {k: data[k] for k in depths}
    return reachable, depths


async def _http_get_json(session: aiohttp.ClientSession, url: str) -> dict:
    """HTTP GET with retry + exponential backoff. Returns parsed JSON."""
    async with _semaphore, _rate:
        for attempt in range(RETRIES):
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT),
                    ssl=False,
                ) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            except Exception:
                if attempt == RETRIES - 1:
                    raise
                await asyncio.sleep(0.5 * (2 ** attempt))
        raise RuntimeError(f"Failed after {RETRIES} retries: {url}")


def _extract_category_from_url(url: str) -> Optional[str]:
    """Extract the SMW category name from a category page URL."""
    for suffix in CATEGORY_URL_TO_NAME:
        if url.endswith(suffix) or url.endswith(quote(suffix, safe=":")):
            return suffix
    return None


def _http_get_json_sync(url: str) -> dict:
    """Sync HTTP GET with retry. Used by get_all_data which routes call sync."""
    import time
    import requests
    last_err = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, timeout=HTTP_TIMEOUT, verify=False)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_err = e
            time.sleep(0.5 * (2 ** attempt))
    raise RuntimeError(f"Failed after {RETRIES} retries: {url}; last error: {last_err}")


def get_all_data(category_url: str) -> list:
    """Return a list of normalized page-keys belonging to a category.

    Accepts the legacy category URL format
    (e.g. "https://oppekava.edu.ee/a/Kategooria:Haridus:Oskus").
    """
    from logic.graph_utils import normalize_key

    category = _extract_category_from_url(category_url)
    if not category:
        return []

    out = []
    offset = 0
    while True:
        url = build_query(category, [], offset=offset, limit=PAGE_SIZE)
        data = _http_get_json_sync(url)
        results = data.get("query", {}).get("results", {}) or {}
        for page_title in results.keys():
            out.append(normalize_key(page_title))
        if len(results) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return out


async def parse_all_data_async(data_list: list) -> tuple:
    """Drop-in replacement for the legacy parse_all_data_async.

    Fetches every configured category from the SMW ask API in parallel,
    merges into one in-memory data dict keyed by normalize_key(page_title),
    then BFS-filters to nodes reachable from `data_list` seeds (respecting
    module-level LIMIT_RECURSION / MAX_DEPTH).
    """
    from logic.graph_utils import normalize_key

    merged: dict = {}

    async with aiohttp.ClientSession() as session:
        async def fetch_one(cat_name: str, node_type: str):
            """Fetch one category, retrying the whole category on failure.

            Returns (cat_name, nodes_or_None). None signals the category could
            not be loaded after CATEGORY_RETRIES attempts so the caller can
            fail loudly instead of silently dropping the whole category.
            """
            attrs = ATTRIBUTES_BY_TYPE.get(node_type, [])
            last_err = None
            for attempt in range(CATEGORY_RETRIES):
                try:
                    nodes = await fetch_category(
                        cat_name, attrs, node_type, session=session)
                    return cat_name, nodes
                except Exception as e:
                    last_err = e
                    print(f"[warn] fetch_category({cat_name}) attempt "
                          f"{attempt + 1}/{CATEGORY_RETRIES} failed: {e}")
                    if attempt < CATEGORY_RETRIES - 1:
                        await asyncio.sleep(0.5 * (2 ** attempt))
            print(f"[error] fetch_category({cat_name}) gave up after "
                  f"{CATEGORY_RETRIES} attempts: {last_err}")
            return cat_name, None

        tasks = [
            fetch_one(cat_name, node_type)
            for cat_name, node_type in CATEGORY_URL_TO_NAME.values()
        ]
        results = await asyncio.gather(*tasks)

    failed = [cat_name for cat_name, nodes in results if nodes is None]
    if failed:
        # Never persist / serve an incomplete graph: surface the failure so the
        # caller keeps the previous (complete) cache instead of overwriting it.
        raise RuntimeError(
            "Failed to load categories after retries: " + ", ".join(failed))

    for _cat_name, partial in results:
        for raw_title, node in partial.items():
            merged[normalize_key(raw_title)] = node

    seeds = [normalize_key(s) for s in data_list]
    return _bfs_filter(
        merged,
        seeds=seeds,
        limit_recursion=LIMIT_RECURSION,
        max_depth=MAX_DEPTH,
    )


async def fetch_category(
    category: str,
    attrs: list,
    node_type: str,
    session: Optional[aiohttp.ClientSession] = None,
) -> dict:
    """Fetch all pages in a category via paginated ask API.

    Returns dict keyed by RAW page_title (with underscores) -> node dict.
    Caller normalizes keys when merging.
    """
    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()
    try:
        out = {}
        offset = 0
        while True:
            url = build_query(category, attrs, offset=offset, limit=PAGE_SIZE)
            data = await _http_get_json(session, url)
            results = data.get("query", {}).get("results", {}) or {}
            for page_title, page_data in results.items():
                out[page_title] = parse_page_to_node(page_title, page_data, node_type)
            if len(results) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        return out
    finally:
        if own_session:
            await session.close()


def build_query(category: str, attrs: list, offset: int = 0,
                 limit: int = PAGE_SIZE) -> str:
    """Build an SMW ask API URL for a category query.

    Args:
        category: SMW category name (e.g. "Haridus:Oskus").
        attrs: List of printout attribute names with namespace
               (e.g. "Schema:description", "Haridus:esco_link").
        offset: Pagination offset.
        limit: Page size.
    """
    parts = [f"[[Category:{category}]]", "[[Modification date::+]]",
             "?Modification date"]
    for attr in attrs:
        parts.append(f"?{attr}")
    parts.extend([
        "sort=Modification date",
        "order=desc",
        f"limit={limit}",
        f"offset={offset}",
    ])
    query = "|".join(parts)
    return f"{BASE_URL}?action=ask&format=json&query={quote(query, safe='')}"
