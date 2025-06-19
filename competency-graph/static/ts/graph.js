var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var selectedSkills = new Set();
function updateSelectedSkillsDisplay() {
    var container = document.getElementById("selectedSkills");
    var hiddenInput = document.getElementById("jobSkills");
    container.innerHTML = "";
    selectedSkills.forEach(function (skill) {
        var badge = document.createElement("span");
        badge.className = "badge bg-info text-dark p-2";
        badge.textContent = skill;
        badge.style.cursor = "pointer";
        badge.onclick = function () {
            selectedSkills.delete(skill);
            updateSelectedSkillsDisplay();
        };
        container.appendChild(badge);
    });
    hiddenInput.value = Array.from(selectedSkills).join(",");
}
function drawGraph(skill) {
    return __awaiter(this, void 0, void 0, function () {
        var loading, response, container_1, _a, nodes, edges, container, data, options, network;
        return __generator(this, function (_b) {
            switch (_b.label) {
                case 0:
                    loading = document.getElementById("loading");
                    loading.style.display = "block";
                    return [4 /*yield*/, fetch("/graph?skill=".concat(encodeURIComponent(skill)))];
                case 1:
                    response = _b.sent();
                    if (!response.ok) {
                        container_1 = document.getElementById("network");
                        container_1.innerHTML = "";
                        alert("Oskust ei leitud");
                        return [2 /*return*/];
                    }
                    return [4 /*yield*/, response.json()];
                case 2:
                    _a = _b.sent(), nodes = _a.nodes, edges = _a.edges;
                    loading.style.display = "none";
                    container = document.getElementById("network");
                    data = {
                        nodes: new vis.DataSet(nodes),
                        edges: new vis.DataSet(edges)
                    };
                    options = {
                        nodes: {
                            shape: "dot",
                            font: { size: 16, color: "#343434" },
                            borderWidth: 2
                        },
                        edges: {
                            arrows: "to",
                            color: { color: "#cccccc", highlight: "#999999" },
                            width: 1.5,
                            smooth: { type: "dynamic" }
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
                    network = new vis.Network(container, data, options);
                    network.on("click", function (params) {
                        if (params.nodes.length > 0) {
                            var nodeId = params.nodes[0];
                            var node = data.nodes.get(nodeId);
                            // Eemalda linkimine, ainult lisa oskus
                            selectedSkills.add(node.label);
                            updateSelectedSkillsDisplay();
                        }
                    });
                    network.on("hoverNode", function (params) {
                        var nodeId = params.node;
                        var node = data.nodes.get(nodeId);
                        document.getElementById("infoTitle").textContent = node.label;
                        document.getElementById("infoDescription").textContent = node.title || "Kirjeldus puudub";
                        var link = document.getElementById("infoLink");
                        if (node.link) {
                            link.href = node.link;
                            link.style.display = "inline-block";
                        }
                        else {
                            link.style.display = "none";
                        }
                        var extra = "";
                        if (node.esco_link) {
                            extra += "<p><strong>ESCO link:</strong> <a href=\"".concat(node.esco_link, "\" target=\"_blank\">Vaata ESCO</a></p>");
                        }
                        if (node.esco_vaste) {
                            extra += "<p><strong>ESCO vaste:</strong> <a href=\"".concat(node.esco_vaste, "\" target=\"_blank\">").concat(node.esco_vaste, "</a></p>");
                        }
                        if (node.skill_verb) {
                            extra += "<p><strong>Verb:</strong> <a href=\"".concat(node.skill_verb, "\" target=\"_blank\">").concat(node.skill_verb, "</a></p>");
                        }
                        if (node.osk_reg_kood) {
                            extra += "<p><strong>Oskusregistri kood:</strong> \n        <a href=\"https://oska.kutsekoda.ee/oskuste_register/oskused/".concat(node.osk_reg_kood, "\" target=\"_blank\">").concat(node.osk_reg_kood, "</a></p>");
                        }
                        document.getElementById("infoExtra").innerHTML = extra;
                    });
                    return [2 /*return*/];
            }
        });
    });
}
document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("searchForm");
    var input = document.getElementById("skillInput");
    form.onsubmit = function (e) {
        e.preventDefault();
        drawGraph(input.value.trim());
    };
    drawGraph(input.value.trim());
});
