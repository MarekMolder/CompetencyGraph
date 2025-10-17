"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
const selectedSkills = new Set();
let nodes, edges;
let network;
let lastClickedNode = null;
let isJobCreationMode = false;
function enableJobCreationMode() {
    isJobCreationMode = true;
}
function disableJobCreationMode() {
    isJobCreationMode = false;
}
function updateSelectedSkillsDisplay() {
    const container = document.getElementById("selectedSkills");
    const hiddenInput = document.getElementById("jobSkills");
    container.innerHTML = "";
    for (const skill of selectedSkills) {
        const badge = createSkillBadge(skill);
        container.appendChild(badge);
    }
    hiddenInput.value = Array.from(selectedSkills).join(",");
}
function createSkillBadge(skill) {
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
function drawGraph(skill) {
    return __awaiter(this, void 0, void 0, function* () {
        const loading = document.getElementById("loading");
        loading.style.display = "block";
        try {
            const response = yield fetch(`/graph?skill=${encodeURIComponent(skill)}`);
            if (!response.ok)
                throw new Error("Oskust ei leitud");
            const responseData = yield response.json();
            renderGraph(responseData.nodes, responseData.edges);
        }
        catch (error) {
            showError("Oskust ei leitud");
        }
        finally {
            loading.style.display = "none";
        }
    });
}
function filterGraphBySearch(term) {
    const lower = term.toLowerCase();
    let matchedNode = null;
    // Leia esimene sobiv node
    nodes.get().forEach((n) => {
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
    recomputeVisibility();
}
function renderGraph(nodesData, edgesData) {
    const container = document.getElementById("network");
    const defaultNodeColor = {
        background: "#ffffff",
        border: "#007bff",
        highlight: { background: "#e0f0ff", border: "#0056b3" }
    };
    nodes = new vis.DataSet(nodesData.map(n => {
        var _a;
        return (Object.assign(Object.assign({}, n), { color: n.color || defaultNodeColor, borderWidth: (_a = n.borderWidth) !== null && _a !== void 0 ? _a : 1 }));
    }));
    edges = new vis.DataSet(edgesData.map(e => (Object.assign(Object.assign({}, e), { color: e.color || "#cccccc" }))));
    network = new vis.Network(container, { nodes, edges }, getGraphOptions());
    const dropdown = document.getElementById("searchDropdown");
    dropdown.innerHTML = nodes
        .get()
        .slice(0, 200)
        .map((n) => `<li><a class="dropdown-item" href="#" data-id="${n.id}">${n.label}</a></li>`)
        .join("");
    // Ühtne click-handler
    network.on("click", (params) => {
        if (params.nodes.length === 0) {
            if (lastClickedNode)
                resetNodeStyle(lastClickedNode.id);
            lastClickedNode = null;
            isPanelPinned = false;
            hideNodeInfo();
            recomputeVisibility();
            return;
        }
        const clickedId = params.nodes[0];
        const node = nodes.get(clickedId);
        if (isJobCreationMode) {
            if (!selectedSkills.has(node.label)) {
                selectedSkills.add(node.label);
                updateSelectedSkillsDisplay();
            }
            return;
        }
        if (lastClickedNode)
            resetNodeStyle(lastClickedNode.id);
        nodes.update({
            id: clickedId,
            color: {
                background: "#007bff",
                border: "#f89090",
                highlight: { background: "#0056b3", border: "#f89090" }
            },
            borderWidth: 0.5
        });
        lastClickedNode = node;
        updateNodeInfo(node);
        isPanelPinned = true;
        recomputeVisibility();
    });
    network.on("hoverNode", (params) => !isPanelPinned && updateNodeInfo(nodes.get(params.node)));
    network.on("blurNode", hideNodeInfo);
}
function resetNodeStyle(id) {
    nodes.update({
        id,
        color: { background: "#ffffff", border: "#007bff", highlight: { background: "#e0f0ff", border: "#0056b3" } },
        borderWidth: 1
    });
}
function showError(message) {
    const container = document.getElementById("network");
    container.innerHTML = "";
    alert(message);
}
function getGraphOptions() {
    return {
        nodes: {
            shape: "dot",
            size: 20,
            font: {
                size: 20,
                color: "#333",
                face: "arial",
                vadjust: 0,
                multi: "html",
                maxWidth: 300, // 🟢 piirab tekstirida, et see murraks
            },
            margin: 10,
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
            navigationButtons: true,
            keyboard: false,
            zoomView: true
        },
        layout: { improvedLayout: true },
        physics: {
            enabled: true,
            solver: "forceAtlas2Based",
            stabilization: { enabled: true, iterations: 250, updateInterval: 25, fit: true },
            forceAtlas2Based: {
                gravitationalConstant: -45, // väiksem tõuge → klastrid lähemal
                centralGravity: 0.004, // tugevam tõmme keskpunkti
                springLength: 130, // veidi lühemad ühendused
                springConstant: 0.025, // pisut jäigemad ühendused
                avoidOverlap: 0.7 // hoiab sildid loetavana, aga mitte üle paisutatult
            },
            maxVelocity: 25,
            minVelocity: 0.5,
            timestep: 0.5,
            adaptiveTimestep: true,
        },
    };
}
let isPanelPinned = false; // uus flag
function updateNodeInfo(node) {
    const panel = document.getElementById("skillInfo");
    panel.classList.add("show");
    document.getElementById("infoTitle").textContent = node.label;
    document.getElementById("infoDescription").textContent = node.description || "Kirjeldus puudub";
    const link = document.getElementById("infoLink");
    if (node.link) {
        link.href = node.link;
        link.style.display = "inline-block";
    }
    else {
        link.style.display = "none";
    }
    const extraInfo = formatExtraNodeInfo(node);
    document.getElementById("infoExtra").innerHTML = extraInfo;
}
function hideNodeInfo() {
    if (!isPanelPinned) {
        document.getElementById("skillInfo").classList.remove("show");
    }
}
function formatExtraNodeInfo(node) {
    const info = [];
    if (node.esco_link)
        info.push(`<p><strong>ESCO link:</strong> <a href="${node.esco_link}" target="_blank">${node.esco_link}</a></p>`);
    if (node.esco_vaste)
        info.push(`<p><strong>ESCO vaste:</strong> <a href="${node.esco_vaste}" target="_blank">${node.esco_vaste}</a></p>`);
    if (node.skill_verb)
        info.push(`<p><strong>Verb:</strong> <a href="${node.skill_verb}" target="_blank">${node.skill_verb}</a></p>`);
    if (node.osk_reg_kood) {
        info.push(`<p><strong>Oskusregistri kood:</strong> <a href="https://oska.kutsekoda.ee/oskuste_register/oskused/${node.osk_reg_kood}" target="_blank">${node.osk_reg_kood}</a></p>`);
    }
    ;
    if (node.relevant_occupations && node.relevant_occupations.length > 0) {
        const occLinks = node.relevant_occupations.map((o) => `<a href="${o.uri}" target="_blank">${o.label}</a>`).join(", ");
        info.push(`<p><strong>Seotud ametid:</strong> ${occLinks}</p>`);
    }
    // --- Õpiväljundi lisainfo ---
    if (node.klass)
        info.push(`<p><strong>Klass:</strong> ${node.klass}</p>`);
    if (node.kooliaste)
        info.push(`<p><strong>Kooliaste:</strong> ${node.kooliaste}</p>`);
    if (node.seotud_oppeaine)
        info.push(`<p><strong>Seotud õppeaine:</strong> 
      <a href="${node.seotud_oppeaine}" target="_blank">${node.seotud_oppeaine.replace("http://oppekava.edu.ee/a/Special:URIResolver/", "").replaceAll("_", " ")}</a>
    </p>`);
    if (node.seotud_teema)
        info.push(`<p><strong>Seotud teema:</strong> 
      <a href="${node.seotud_teema}" target="_blank">${node.seotud_teema.replace("http://oppekava.edu.ee/a/Special:URIResolver/", "").replaceAll("_", " ")}</a>
    </p>`);
    return info.join("");
}
// Init
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("searchForm");
    const input = document.getElementById("skillInput");
    const dropdown = document.getElementById("searchDropdown");
    form.onsubmit = (e) => {
        e.preventDefault();
        const term = input.value.trim();
        if (!term) {
            // kui tühi otsing → näita kõike
            nodes.get().forEach((n) => nodes.update({ id: n.id, hidden: false }));
            edges.get().forEach((e) => edges.update({ id: e.id, hidden: false }));
            lastClickedNode = null;
            return;
        }
        if (nodes && edges) {
            filterGraphBySearch(term);
        }
        else {
            drawGraph("").then(() => filterGraphBySearch(term));
        }
    };
    input.addEventListener("input", () => {
        if (!nodes)
            return;
        const term = input.value.toLowerCase();
        if (!term) {
            dropdown.innerHTML = "";
            dropdown.classList.remove("show");
            return;
        }
        const matches = nodes.get()
            .filter((n) => n.label.toLowerCase().includes(term))
            .slice(0, 30);
        dropdown.innerHTML = matches.map((n) => `<li><a class="dropdown-item" href="javascript:void(0)" data-id="${n.id}">${n.label}</a></li>`).join("");
        if (matches.length > 0)
            dropdown.classList.add("show");
        else
            dropdown.classList.remove("show");
    });
    dropdown.addEventListener("click", (e) => {
        const target = e.target;
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
function getCheckbox(id, def = true) {
    const el = document.getElementById(id);
    return el ? el.checked : def;
}
function recomputeVisibility() {
    if (!nodes || !edges)
        return;
    const levelEl = document.getElementById("levelSelect");
    const selectedDepth = levelEl ? parseInt(levelEl.value, 10) : 99;
    const onlyPrereq = getCheckbox("showOnlyPrerequisites", false);
    const typeFilters = {
        oskus: getCheckbox("filterOskus"),
        kompetents: getCheckbox("filterKompetents"),
        tegevusnaitaja: getCheckbox("filterTn"),
        knobit: getCheckbox("filterKnobit"),
        opivaljund: getCheckbox("filterOpivaljund"),
        muu: getCheckbox("filterMuu")
    };
    const edgeFilters = {
        "eeldab": getCheckbox("filterEdgeEeldab"),
        "koosneb": getCheckbox("filterEdgeKoosneb"),
        "sisaldab Tn": getCheckbox("filterEdgeSisaldabTn"),
        "sisaldab knobitit": getCheckbox("filterEdgeSisaldabKnobitit"),
        "Tn eeldab": getCheckbox("filterEdgeTnEeldab"),
        "sisaldab knobitit (OV)": getCheckbox("filterEdgeOvKnobit"),
        "eeldab (OV)": getCheckbox("filterEdgeOvEeldab"),
    };
    const allNodes = nodes.get();
    const allEdges = edges.get();
    const adjAll = {};
    const adjEeldab = {};
    for (const e of allEdges) {
        if (!adjAll[e.from])
            adjAll[e.from] = [];
        if (!adjAll[e.to])
            adjAll[e.to] = [];
        adjAll[e.from].push(e.to);
        adjAll[e.to].push(e.from);
        if (e.label === "eeldab") {
            if (!adjEeldab[e.from])
                adjEeldab[e.from] = [];
            if (!adjEeldab[e.to])
                adjEeldab[e.to] = [];
            adjEeldab[e.from].push(e.to);
            adjEeldab[e.to].push(e.from);
        }
    }
    let baseVisible = new Set();
    if (!lastClickedNode || selectedDepth === 99) {
        for (const n of allNodes)
            baseVisible.add(n.id);
    }
    else {
        const queue = [{ id: lastClickedNode.id, depth: 0 }];
        const adj = onlyPrereq ? adjEeldab : adjAll;
        baseVisible.add(lastClickedNode.id);
        while (queue.length) {
            const { id, depth } = queue.shift();
            if (depth >= selectedDepth)
                continue;
            for (const nb of adj[id] || []) {
                if (!baseVisible.has(nb)) {
                    baseVisible.add(nb);
                    queue.push({ id: nb, depth: depth + 1 });
                }
            }
        }
    }
    const nodeHidden = {};
    const nodeUpdates = allNodes.map((n) => {
        var _a;
        const visible = baseVisible.has(n.id) && ((_a = typeFilters[n.type]) !== null && _a !== void 0 ? _a : true);
        nodeHidden[n.id] = !visible;
        return { id: n.id, hidden: !visible };
    });
    nodes.update(nodeUpdates);
    const edgeUpdates = allEdges.map((e) => {
        var _a;
        const fromVis = !nodeHidden[e.from];
        const toVis = !nodeHidden[e.to];
        const typeOk = (_a = edgeFilters[e.label]) !== null && _a !== void 0 ? _a : true;
        const prereqOk = !onlyPrereq || e.label === "eeldab";
        return { id: e.id, hidden: !(fromVis && toVis && typeOk && prereqOk) };
    });
    edges.update(edgeUpdates);
}
