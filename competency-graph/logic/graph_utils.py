import json
import os
import re
from urllib.parse import unquote

DISPLAY_URL = "https://oppekava.edu.ee/a/"
SKILLS_URL = "https://oppekava.edu.ee/a/Kategooria:Haridus:Oskus"
COMPETENCIES_URL = "https://oppekava.edu.ee/a/Kategooria:Haridus:Kompetents"
TEGEVUSNAITAJAD_URL = "https://oppekava.edu.ee/a/Kategooria:Haridus:Tegevusnaitaja"
KNOBITID_URL = "https://oppekava.edu.ee/a/Kategooria:Haridus:Knobit"
OPIVALJUNDID_URL = "https://oppekava.edu.ee/a/Kategooria:Haridus:Opivaljund"
AMETIKOMPETENTSIPROFIIL_URL = "https://oppekava.edu.ee/a/Kategooria:Haridus:AmetiKompetentsiProfiil"
OPPEAINE_TASEMEOPE_URL = "https://oppekava.edu.ee/a/Kategooria:Haridus:OppeaineTasemeOpe"
VALDKONNA_KOMPETENTSIPROFIIL_URL = "https://oppekava.edu.ee/a/Kategooria:Haridus:ValdkonnaKompetentsiProfiil"
OPPEKAVA_URL = "https://oppekava.edu.ee/a/Kategooria:Haridus:Oppekava"

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELATION_CONFIG_PATH = os.path.join(_BASE_DIR, "data", "relation_config.json")


SMW_HEX_RE = re.compile(r'-(?P<h>[0-9A-Fa-f]{2})')


def decode_smw_hex(s: str) -> str:
    """Decode SMW's -XX hex escapes (e.g. -2C -> ',') in ASCII printable range."""
    def repl(m):
        code = int(m.group('h'), 16)
        ch = chr(code)
        if 0x20 <= code <= 0x7E:
            return ch
        return m.group(0)
    return SMW_HEX_RE.sub(repl, s)


def uri_to_skill_name(uri: str) -> str:
    frag = unquote(uri.split("/")[-1])
    return decode_smw_hex(frag)


def uri_to_label(uri: str) -> str:
    frag = unquote(uri.split("/")[-1])
    return decode_smw_hex(frag).replace("_", " ")


def normalize_key(s: str) -> str:
    """Canonical key: decode hex, strip, underscore-collapse, drop trailing (NN)."""
    s = unquote(s)
    s = decode_smw_hex(s)
    s = s.strip()
    s = s.replace(" ", "_")
    s = re.sub(r"_+", "_", s)
    s = re.sub(r"\(\d{1,2}\)$", "", s)
    return s


def _skill_key(skill_name: str) -> str:
    return normalize_key(skill_name)


def load_relation_config() -> dict:
    if os.path.exists(RELATION_CONFIG_PATH):
        with open(RELATION_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


from logic.ask_api import parse_all_data_async, get_all_data
from logic import ask_api

LIMIT_RECURSION = ask_api.LIMIT_RECURSION
MAX_DEPTH = ask_api.MAX_DEPTH
