# Oskuste Graaf Visualiseerija

See projekt visualiseerib Eesti oskuste registri andmeid graafina, võimaldades uurida oskuste omavahelisi seoseid, struktuuri ja hierarhiat. Kasutatakse andmeid portaalist [oppekava.edu.ee](https://oppekava.edu.ee) ning visualiseeritakse need interaktiivsel viisil veebis ja/või töölaual.

## Funktsionaalsus

- Loeb kõik oskused kategoorialehelt [oppekava.edu.ee](https://oppekava.edu.ee/a/Kategooria:Haridus:Oskus)
- Parsib iga oskuse RDF-andmed, leiab alam-oskused ja seotud metaandmed
- Visualiseerib oskuste sõltuvusgraafi veebis (`pyvis`) või ekspordib `GraphML` formaati (`networkx`)
- Toetab otsingut ja sõlmede filtreerimist sügavuse või nime alusel
- Sisaldab Flaski-põhist veebiliidest, kus kasutaja saab oskusi otsida, visualiseerida ja ametikohti luua/hallata

## Paigaldus

1. Veendu, et sul on Python 3.8+ paigaldatud
2. Klona repositoorium ja paigalda sõltuvused:

```bash
pip install -r docs/requirements.txt
```

## Kasutamine

### 1. Graafi genereerimine käsurealt
```bash
python logic/graph_utils.py
```
See loob järgmised failid:
- `skill_graph.html` – interaktiivne visualiseerimine brauseris
- `skills_graph.graphml` – eksporditud graaf analüüsiks Gephi vms tööriistaga

### 2. Veebirakendus Flaskiga
```bash
python run.py
```
Avaneb rakendus, kus saad:
- Sisestada oskus ja visualiseerida selle sõltuvusi
- Hallata ametikohtade loendit (loetelu, lisamine, muutmine, kustutamine)

## Projekti struktuur

```
.
├── app/
│   ├── __init__.py
│   ├── routes/
│   │   ├── graph_routes.py
│   │   └── job_routes.py
│   └── templates/
│       ├── index.html
│       └── ametikohad.html
├── docs/
│   ├── requirements.txt
│   ├── api.md
│   └── arhitecture.md
├── logic/
│   ├── graph_utils.py
│   └── job_utils.py
├── static/
│   └── js/
│       └── graph.js
│   └── ts/
│       └── graph.ts
├── run.py
├── README-EST.md
├── README_ENG.md
```

## Failide kirjeldus
- `graph_utils.py` – oskuste RDF-andmete laadimine ja graafi ehitus
- `job_utils.py` – ametikohtade (JSON-andmete) laadimine ja salvestamine
- `graph.js` – kliendipoolne visualiseerimise loogika (Vis.js)
- `graph_routes.py` – oskuste graafi API endpoint
- `job_routes.py` – ametikohtade haldamise API
- `index.html` – oskuse otsing ja visualiseerimine
- `ametikohad.html` – ametikohtade CRUD-liides

## Autor
Marek Mölder