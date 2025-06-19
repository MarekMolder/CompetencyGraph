# Project Architecture

This project is structured to separate logic, presentation, and routing concerns clearly, following good maintainability and modularity principles.

## Overview

The application has two main modes:

1. **Graph Generator (CLI-based)** – Generates a skills graph from RDF data and outputs HTML and GraphML.
2. **Web Interface (Flask-based)** – Allows users to explore the skills graph interactively and manage job entries.

---

## Directory Structure

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

## Component Breakdown

### `graph_utils.py`
- Parses RDF data from `oppekava.edu.ee`
- Builds skill dependency graph recursively
- Outputs:
  - Interactive HTML via Pyvis
  - `.graphml` file for external analysis

### `job_utils.py`
- Loads and saves job data from `ametikohad.json`
- Simple JSON-based persistence layer

### Flask app (`run.py`)
- Registers Blueprints from `app/routes/`
- Defines endpoints for:
  - Graph generation (`/graph`)
  - Job management (CRUD for jobs)
  - Homepage and job page rendering

### Frontend (`graph.js`)
- Draws skill graph using [Vis.js](https://visjs.org/)
- Allows searching, clicking, and filtering nodes
- Updates a list of selected skills visually

---

## Technologies Used

- **Flask**: lightweight web framework
- **rdflib**: RDF parsing
- **BeautifulSoup4**: HTML scraping
- **Pyvis**: Interactive graph visualization
- **NetworkX**: GraphML export
- **Vis.js**: Browser-side rendering of graphs