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
function renderGraph(nodesData, edgesData) {
    const container = document.getElementById("network");
    nodesData.forEach((node) => {
        node.color = {
            background: "#ffffff", // valge sisu
            border: "#007bff", // sinine äär
            highlight: {
                background: "#e0f0ff", // hover
                border: "#0056b3"
            }
        };
        node.borderWidth = 1;
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
    network.on("click", (params) => {
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
        }
        else {
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
    network.on("hoverNode", (params) => {
        const node = nodes.get(params.node);
        updateNodeInfo(node);
    });
}
function applyLevelFilter() {
    const selectedLevel = parseInt(document.getElementById("levelSelect").value);
    if (!lastClickedNode || selectedLevel === 99) {
        nodes.get().forEach((n) => nodes.update({ id: n.id, hidden: false }));
        return;
    }
    const queue = [{ id: lastClickedNode.id, depth: 0 }];
    const visible = new Set([lastClickedNode.id]);
    for (let i = 0; i < queue.length; i++) {
        const { id, depth } = queue[i];
        if (depth >= selectedLevel)
            continue;
        edges.get().forEach((edge) => {
            if (edge.from === id && !visible.has(edge.to)) {
                visible.add(edge.to);
                queue.push({ id: edge.to, depth: depth + 1 });
            }
            else if (edge.to === id && !visible.has(edge.from)) {
                visible.add(edge.from);
                queue.push({ id: edge.from, depth: depth + 1 });
            }
        });
    }
    nodes.get().forEach((n) => {
        nodes.update({ id: n.id, hidden: !visible.has(n.id) });
    });
}
function applyEdgeFilter() {
    const checkbox = document.getElementById("showOnlyPrerequisites");
    const showOnlyPrerequisites = checkbox.checked;
    if (!lastClickedNode)
        return;
    if (showOnlyPrerequisites) {
        const visibleNodeIds = new Set();
        const visibleEdgeIds = new Set();
        // BFS eeldab-seostele
        const queue = [lastClickedNode.id];
        visibleNodeIds.add(lastClickedNode.id);
        while (queue.length > 0) {
            const current = queue.shift();
            edges.get().forEach((edge) => {
                if (edge.label === "eeldab") {
                    if (edge.from === current && !visibleNodeIds.has(edge.to)) {
                        visibleNodeIds.add(edge.to);
                        visibleEdgeIds.add(edge.id);
                        queue.push(edge.to);
                    }
                    else if (edge.to === current && !visibleNodeIds.has(edge.from)) {
                        visibleNodeIds.add(edge.from);
                        visibleEdgeIds.add(edge.id);
                        queue.push(edge.from);
                    }
                    else if (edge.from === current || edge.to === current) {
                        visibleEdgeIds.add(edge.id); // Lisa serv, kui üks ots juba olemas
                    }
                }
            });
        }
        // Peida kõik node’id, mis ei kuulu eeldab-harusse
        nodes.get().forEach((node) => {
            const isVisible = visibleNodeIds.has(node.id);
            nodes.update({ id: node.id, hidden: !isVisible });
        });
        // Peida kõik muud servad peale eeldab-seoseid
        edges.get().forEach((edge) => {
            const isVisible = visibleEdgeIds.has(edge.id);
            edges.update({ id: edge.id, hidden: !isVisible });
        });
    }
    else {
        // Taasta kõik
        nodes.get().forEach((node) => {
            nodes.update({ id: node.id, hidden: false });
        });
        edges.get().forEach((edge) => {
            edges.update({ id: edge.id, hidden: false });
        });
    }
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
            font: { size: 16, color: "#343434" },
            borderWidth: 2
        },
        edges: {
            arrows: "to",
            color: { color: "#cccccc", highlight: "#999999" },
            width: 1.5,
            smooth: { type: "dynamic" },
            font: {
                align: "top",
                size: 12,
                color: "#333333",
                strokeWidth: 0
            }
        },
        interaction: {
            hover: true,
            navigationButtons: true,
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
function updateNodeInfo(node) {
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
    return info.join("");
}
// Init
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("searchForm");
    const input = document.getElementById("skillInput");
    form.onsubmit = (e) => {
        e.preventDefault();
        const normalizedSkill = normalizeSkill(input.value);
        drawGraph(normalizedSkill);
    };
    drawGraph(normalizeSkill(input.value));
});
function normalizeSkill(text) {
    const trimmed = text.trim();
    if (!trimmed)
        return "";
    return trimmed.charAt(0).toUpperCase() + trimmed.slice(1).toLowerCase();
}
