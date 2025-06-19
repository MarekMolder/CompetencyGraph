# Skills Graph Visualizer

This project visualizes skill dependency data from Estonia’s skills registry as an interactive graph. It allows users to explore how skills are structured and interconnected using RDF data from [oppekava.edu.ee](https://oppekava.edu.ee).

## Features

- Fetches all skills from the [oppekava.edu.ee](https://oppekava.edu.ee/a/Kategooria:Haridus:Oskus) category page
- Parses RDF data for each skill, extracting subskills and metadata
- Visualizes the skill dependency graph interactively using `pyvis`, or exports to `GraphML` using `networkx`
- Supports search and depth-based filtering of nodes
- Includes a Flask web interface for searching skills and managing job entries (CRUD)

## Installation

1. Make sure Python 3.8+ is installed
2. Clone the repository and install dependencies:

```bash
pip install -r docs/requirements.txt
```

## Usage

### 1. Generate the graph via command-line
```bash
python logic/graph_utils.py
```
This creates the following files:
- `skill_graph.html` – interactive visualization viewable in a browser
- `skills_graph.graphml` – exportable format for tools like Gephi or Cytoscape

### 2. Launch the web application with Flask
```bash
python run.py
```
The web interface lets you:
- Search a skill and visualize its dependencies
- Manage job entries (list, create, edit, delete)

## Project Structure

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
│   └── architecture.md
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

## File Descriptions
- `graph_utils.py` – logic for loading RDF data and building the skill graph
- `job_utils.py` – handles loading and saving job data from JSON
- `graph.js` – client-side graph logic using Vis.js
- `graph_routes.py` – API endpoints for graph data
- `job_routes.py` – API endpoints for job management
- `index.html` – interface for skill input and graph display
- `ametikohad.html` – interface for job listing and editing

## Author
Marek Mölder
