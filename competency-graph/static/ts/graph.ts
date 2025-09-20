declare var vis: any;

const selectedSkills = new Set<string>();
let nodes: any, edges: any;
let network: any;
let lastClickedNode: any = null;
let isJobCreationMode = false;

function enableJobCreationMode(): void {
  isJobCreationMode = true;
}

function disableJobCreationMode(): void {
  isJobCreationMode = false;
}

function updateSelectedSkillsDisplay(): void {
  const container = document.getElementById("selectedSkills")!;
  const hiddenInput = document.getElementById("jobSkills") as HTMLInputElement;

  container.innerHTML = "";
  for (const skill of selectedSkills) {
    const badge = createSkillBadge(skill);
    container.appendChild(badge);
  }

  hiddenInput.value = Array.from(selectedSkills).join(",");
}

function createSkillBadge(skill: string): HTMLElement {
  const badge = document.createElement("span");
  badge.className = "badge bg-info text-dark p-2";
  badge.textContent = skill;
  badge.style.cursor = "pointer";
  badge.onclick = () => {
    selectedSkills.delete(skill);
    updateSelectedSkillsDisplay();
  };
  return badge;
}

async function drawGraph(skill: string): Promise<void> {
  const loading = document.getElementById("loading")!;
  loading.style.display = "block";

  try {
    const response = await fetch(`/graph?skill=${encodeURIComponent(skill)}`);
    if (!response.ok) throw new Error("Oskust ei leitud");

    const responseData = await response.json();
    renderGraph(responseData.nodes, responseData.edges);
  } catch (error) {
    showError("Oskust ei leitud");
  } finally {
    loading.style.display = "none";
  }
}

function filterGraphBySearch(term: string): void {
  const lower = term.toLowerCase();
  let matchedNode: any = null;

  // Leia esimene sobiv node
  nodes.get().forEach((n: any) => {
    if (!matchedNode && n.label.toLowerCase().includes(lower)) {
      matchedNode = n;
    }
  });

  if (!matchedNode) {
    alert("Ei leitud");
    return;
  }

  lastClickedNode = matchedNode;

  // Tõsta fookus
  network.focus(matchedNode.id, {
    scale: 1.2,
    animation: { duration: 800, easingFunction: "easeInOutQuad" }
  });

  updateNodeInfo(matchedNode);

  // RAKENDA sügavuse filter, et näidata õige hulk node’e + kaared
  applyLevelFilter();
}


function renderGraph(nodesData: any[], edgesData: any[]): void {
  const container = document.getElementById("network")!;

    nodesData.forEach((node) => {
      if (!node.color) {
        node.color = {
          background: "#ffffff",
          border: "#007bff",
          highlight: {
            background: "#e0f0ff",
            border: "#0056b3"
          }
        };
        node.borderWidth = 1;
      }
    });

  edgesData.forEach((edge) => {
    if (!edge.color) {
      edge.color = "#cccccc"; // fallback värv
    }
  });

  nodes = new vis.DataSet(nodesData);
  edges = new vis.DataSet(edgesData);

  const data = { nodes, edges };
  const options = getGraphOptions();
  network = new vis.Network(container, data, options);

  const dropdown = document.getElementById("searchDropdown") as HTMLElement;
  dropdown.innerHTML = nodes.get().slice(0, 200).map((n: any) =>
    `<li><a class="dropdown-item" href="#" data-id="${n.id}">${n.label}</a></li>`
  ).join("");

  network.on("click", (params: any) => {
    if (isJobCreationMode) {
      if (params.nodes.length > 0) {
        const clickedNodeId = params.nodes[0];
        const node = nodes.get(clickedNodeId);

        if (!selectedSkills.has(node.label)) {
          selectedSkills.add(node.label);
          updateSelectedSkillsDisplay();
        }
      }
      return;
    }
    if (params.nodes.length > 0) {
      const clickedNodeId = params.nodes[0];

      // Eemalda eelmine valik
      if (lastClickedNode) {
        nodes.update({
          id: lastClickedNode.id,
          color: {
            background: "#ffffff",
            border: "#007bff",
            highlight: {
              background: "#e0f0ff",
              border: "#0056b3"
            }
          },
          borderWidth: 1
        });
      }

      // Aktiveeri uus
      nodes.update({
        id: clickedNodeId,
        color: {
          background: "#007bff",
          border: "#f89090",
          highlight: {
            background: "#0056b3",
            border: "#f89090"
          }
        },
        borderWidth: 0.5
      });

      lastClickedNode = nodes.get(clickedNodeId);
      applyLevelFilter();

    } else {
      // Klikiti tühjale – eemalda valik
      if (lastClickedNode) {
        nodes.update({
          id: lastClickedNode.id,
          color: {
            background: "#ffffff",
            border: "#007bff",
            highlight: {
              background: "#e0f0ff",
              border: "#0056b3"
            }
          },
          borderWidth: 1
        });
        lastClickedNode = null;
        applyLevelFilter();
      }
    }
  });


network.on("hoverNode", (params: any) => {
  if (!isPanelPinned) {
    const node = nodes.get(params.node);
    updateNodeInfo(node);
  }
});

// Kui hiirega node’ilt ära lähed ja pole pinned → peida
network.on("blurNode", () => {
  hideNodeInfo();
});

// Kui klõpsad node’i peale → paneel lukku
network.on("click", (params: any) => {
  if (params.nodes.length > 0) {
    const clickedNodeId = params.nodes[0];
    const node = nodes.get(clickedNodeId);
    updateNodeInfo(node);
    isPanelPinned = true; // lukusta
  } else {
    // Kui klõpsad tühjale → vabasta
    isPanelPinned = false;
    hideNodeInfo();
  }
});

}

function applyLevelFilter(): void {
  const selectedLevel = parseInt((document.getElementById("levelSelect") as HTMLSelectElement).value);
  if (!lastClickedNode || selectedLevel === 99) {
    nodes.get().forEach((n: any) => nodes.update({ id: n.id, hidden: false }));
    return;
  }

  const queue = [{ id: lastClickedNode.id, depth: 0 }];
  const visible = new Set<string>([lastClickedNode.id]);

  for (let i = 0; i < queue.length; i++) {
    const { id, depth } = queue[i];
    if (depth >= selectedLevel) continue;

    edges.get().forEach((edge: any) => {
      if (edge.from === id && !visible.has(edge.to)) {
        visible.add(edge.to);
        queue.push({ id: edge.to, depth: depth + 1 });
      } else if (edge.to === id && !visible.has(edge.from)) {
        visible.add(edge.from);
        queue.push({ id: edge.from, depth: depth + 1 });
      }
    });
  }

  nodes.get().forEach((n: any) => {
    nodes.update({ id: n.id, hidden: !visible.has(n.id) });
  });
}

function applyEdgeFilter(): void {
  const checkbox = document.getElementById("showOnlyPrerequisites") as HTMLInputElement;
  const showOnlyPrerequisites = checkbox.checked;

  if (!lastClickedNode) return;

  if (showOnlyPrerequisites) {
    const visibleNodeIds = new Set<string>();
    const visibleEdgeIds = new Set<string>();

    // BFS eeldab-seostele
    const queue = [lastClickedNode.id];
    visibleNodeIds.add(lastClickedNode.id);

    while (queue.length > 0) {
      const current = queue.shift();

      edges.get().forEach((edge: any) => {
        if (edge.label === "eeldab") {
          if (edge.from === current && !visibleNodeIds.has(edge.to)) {
            visibleNodeIds.add(edge.to);
            visibleEdgeIds.add(edge.id);
            queue.push(edge.to);
          } else if (edge.to === current && !visibleNodeIds.has(edge.from)) {
            visibleNodeIds.add(edge.from);
            visibleEdgeIds.add(edge.id);
            queue.push(edge.from);
          } else if (edge.from === current || edge.to === current) {
            visibleEdgeIds.add(edge.id); // Lisa serv, kui üks ots juba olemas
          }
        }
      });
    }

    // Peida kõik node’id, mis ei kuulu eeldab-harusse
    nodes.get().forEach((node: any) => {
      const isVisible = visibleNodeIds.has(node.id);
      nodes.update({ id: node.id, hidden: !isVisible });
    });

    // Peida kõik muud servad peale eeldab-seoseid
    edges.get().forEach((edge: any) => {
      const isVisible = visibleEdgeIds.has(edge.id);
      edges.update({ id: edge.id, hidden: !isVisible });
    });

  } else {
    // Taasta kõik
    nodes.get().forEach((node: any) => {
      nodes.update({ id: node.id, hidden: false });
    });
    edges.get().forEach((edge: any) => {
      edges.update({ id: edge.id, hidden: false });
    });
  }
}

function applyEdgeTypeFilter(): void {
  const showEeldab = (document.getElementById("filterEdgeEeldab") as HTMLInputElement).checked;
  const showKoosneb = (document.getElementById("filterEdgeKoosneb") as HTMLInputElement).checked;
  const showSisaldabTn = (document.getElementById("filterEdgeSisaldabTn") as HTMLInputElement).checked;
  const showSisaldabKnobitit = (document.getElementById("filterEdgeSisaldabKnobitit") as HTMLInputElement).checked;
  const showTnEeldab = (document.getElementById("filterEdgeTnEeldab") as HTMLInputElement).checked;

  edges.get().forEach((e: any) => {
    let visible = true;
    switch (e.label) {
      case "eeldab": visible = showEeldab; break;
      case "koosneb": visible = showKoosneb; break;
      case "sisaldab Tn": visible = showSisaldabTn; break;
      case "sisaldab knobitit": visible = showSisaldabKnobitit; break;
      case "Tn eeldab": visible = showTnEeldab; break;
    }

    // Ära näita serva, kui tema node’id on juba peidetud
    const fromVisible = !nodes.get(e.from).hidden;
    const toVisible = !nodes.get(e.to).hidden;
    edges.update({ id: e.id, hidden: !(visible && fromVisible && toVisible) });
  });
}

function showError(message: string): void {
  const container = document.getElementById("network")!;
  container.innerHTML = "";
  alert(message);
}

function getGraphOptions(): any {
  return {
    nodes: {
      shape: "dot",
      font: { size: 16, color: "#5c5c5c" },
      borderWidth: 2
    },
    edges: {
      arrows: "to",
      color: { color: "#cccccc", highlight: "#999999" },
      width: 1.5,
      smooth: { type: "dynamic" },
      font: {
        align: "top",
        size: 16,
        color: "#5c5c5c",
        strokeWidth: 0
      }
    },
    interaction: {
      hover: true,
      navigationButtons: false,
      keyboard: true,
      zoomView: true
    },
    layout: { improvedLayout: true },
    physics: {
      forceAtlas2Based: {
        gravitationalConstant: -80,
        springLength: 110,
        springConstant: 0.05
      },
      solver: "forceAtlas2Based",
      minVelocity: 0.75
    }
  };
}
let isPanelPinned = false; // uus flag

function updateNodeInfo(node: any): void {
  const panel = document.getElementById("skillInfo")!;
  panel.classList.add("show");

  document.getElementById("infoTitle")!.textContent = node.label;
  document.getElementById("infoDescription")!.textContent = node.description || "Kirjeldus puudub";

  const link = document.getElementById("infoLink") as HTMLAnchorElement;
  if (node.link) {
    link.href = node.link;
    link.style.display = "inline-block";
  } else {
    link.style.display = "none";
  }

  const extraInfo = formatExtraNodeInfo(node);
  document.getElementById("infoExtra")!.innerHTML = extraInfo;
}

function hideNodeInfo(): void {
  if (!isPanelPinned) {
    document.getElementById("skillInfo")!.classList.remove("show");
  }
}

function formatExtraNodeInfo(node: any): string {
  const info = [];
  if (node.esco_link) info.push(`<p><strong>ESCO link:</strong> <a href="${node.esco_link}" target="_blank">${node.esco_link}</a></p>`);
  if (node.esco_vaste) info.push(`<p><strong>ESCO vaste:</strong> <a href="${node.esco_vaste}" target="_blank">${node.esco_vaste}</a></p>`);
  if (node.skill_verb) info.push(`<p><strong>Verb:</strong> <a href="${node.skill_verb}" target="_blank">${node.skill_verb}</a></p>`);
  if (node.osk_reg_kood) {
    info.push(`<p><strong>Oskusregistri kood:</strong> <a href="https://oska.kutsekoda.ee/oskuste_register/oskused/${node.osk_reg_kood}" target="_blank">${node.osk_reg_kood}</a></p>`);
  };
  if (node.relevant_occupations && node.relevant_occupations.length > 0) {
      const occLinks = (node.relevant_occupations as { uri: string; label: string }[]).map((o) =>
        `<a href="${o.uri}" target="_blank">${o.label}</a>`
      ).join(", ");
      info.push(`<p><strong>Seotud ametid:</strong> ${occLinks}</p>`);
  }
  return info.join("");
}

// Init

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("searchForm") as HTMLFormElement;
  const input = document.getElementById("skillInput") as HTMLInputElement;
  const dropdown = document.getElementById("searchDropdown") as HTMLElement;

form.onsubmit = (e) => {
  e.preventDefault();
  const term = input.value.trim();
  if (!term) {
    // kui tühi otsing → näita kõike
    nodes.get().forEach((n: any) => nodes.update({ id: n.id, hidden: false }));
    edges.get().forEach((e: any) => edges.update({ id: e.id, hidden: false }));
    lastClickedNode = null;
    return;
  }

  if (nodes && edges) {
    filterGraphBySearch(term);
  } else {
    drawGraph("").then(() => filterGraphBySearch(term));
  }
};

  input.addEventListener("input", () => {
    if (!nodes) return;
    const term = input.value.toLowerCase();
    if (!term) {
      dropdown.innerHTML = "";
      dropdown.classList.remove("show");
      return;
    }

    const matches = nodes.get()
      .filter((n: any) => n.label.toLowerCase().includes(term))
      .slice(0, 30);

    dropdown.innerHTML = matches.map((n: any) =>
      `<li><a class="dropdown-item" href="javascript:void(0)" data-id="${n.id}">${n.label}</a></li>`
    ).join("");

    if (matches.length > 0) dropdown.classList.add("show");
    else dropdown.classList.remove("show");
  });

  dropdown.addEventListener("click", (e: MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.tagName === "A") {
      e.preventDefault();
      const label = target.textContent || "";
      input.value = label;
      dropdown.classList.remove("show");
      filterGraphBySearch(label);
    }
  });

  drawGraph(""); // lae alguses
});

function normalizeSkill(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) return "";
  return trimmed.charAt(0).toUpperCase() + trimmed.slice(1).toLowerCase();
}

function applyTypeFilter(): void {
  const showOskus = (document.getElementById("filterOskus") as HTMLInputElement).checked;
  const showKompetents = (document.getElementById("filterKompetents") as HTMLInputElement).checked;
  const showTn = (document.getElementById("filterTn") as HTMLInputElement).checked;
  const showKnobit = (document.getElementById("filterKnobit") as HTMLInputElement).checked;
  const showMuu = (document.getElementById("filterMuu") as HTMLInputElement).checked;


  nodes.get().forEach((n: any) => {
    let visible = true;
    switch (n.type) {
      case "oskus": visible = showOskus; break;
      case "kompetents": visible = showKompetents; break;
      case "tegevusnaitaja": visible = showTn; break;
      case "knobit": visible = showKnobit; break;
      case "muu": visible = showMuu; break;
    }
    nodes.update({ id: n.id, hidden: !visible });
  });

  // Peida ka servad kui mõlemad otsad on peidetud
  edges.get().forEach((e: any) => {
    const fromVisible = !nodes.get(e.from).hidden;
    const toVisible = !nodes.get(e.to).hidden;
    edges.update({ id: e.id, hidden: !(fromVisible && toVisible) });
  });
}
