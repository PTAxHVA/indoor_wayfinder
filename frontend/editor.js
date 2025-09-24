const API_BASE = ""; // cùng host với backend

// State
let maps = [];
let currentMap = null; // {id, image_url, width, height,...}
let nodes = [];
let edges = [];
let aliasesByNode = {}; // { nodeId: [ {id,name,...}, ... ] }

let mode = "idle"; // idle | add-node | draw-edge
let startNodeId = null;
let tempPoints = []; // polyline đang vẽ
let tempLineEl = null;

const floorSelect = document.getElementById("floorSelect");
const upName = document.getElementById("upName");
const upFloor = document.getElementById("upFloor");
const upPPM = document.getElementById("upPPM");
const upFile = document.getElementById("upFile");
const upBtn = document.getElementById("upBtn");
const upHint = document.getElementById("upHint");

const mapSelect = document.getElementById("mapSelect");
const reloadBtn = document.getElementById("reloadBtn");
const modeBadge = document.getElementById("modeBadge");
const btnAddNode = document.getElementById("modeAddNodeBtn");
const btnDrawEdge = document.getElementById("modeDrawEdgeBtn");
const btnFinishEdge = document.getElementById("finishEdgeBtn");
const btnCancel = document.getElementById("cancelModeBtn");

const mapImage = document.getElementById("mapImage");
const overlay = document.getElementById("overlay");
const mapWrap = document.getElementById("mapWrap");
const board = document.getElementById("board");
const tooltip = document.getElementById("tooltip");

const nodeList = document.getElementById("nodeList");
const edgeList = document.getElementById("edgeList");

// ---------- Helpers ----------
function setMode(m) {
	mode = m;
	modeBadge.textContent =
		"MODE: " +
		(m === "add-node"
			? "Thêm điểm"
			: m === "draw-edge"
			? "Vẽ đường"
			: "Idle");
	overlay.style.pointerEvents = m === "idle" ? "none" : "auto";
	updateFinishBtn();
	if (m !== "draw-edge") {
		clearTemp();
	}
}

function updateFinishBtn() {
	const canFinish =
		mode === "draw-edge" && startNodeId && tempPoints.length >= 2;
	btnFinishEdge.disabled = !canFinish;
}

function clearTemp() {
	startNodeId = null;
	tempPoints = [];
	if (tempLineEl) {
		tempLineEl.remove();
		tempLineEl = null;
	}
	[...overlay.querySelectorAll(".node-dot")].forEach((el) =>
		el.classList.remove("active")
	);
	updateFinishBtn();
}

function clientToImageXY(ev) {
	const rect = mapImage.getBoundingClientRect();
	const scaleX = currentMap.width / rect.width;
	const scaleY = currentMap.height / rect.height;
	const x = (ev.clientX - rect.left) * scaleX;
	const y = (ev.clientY - rect.top) * scaleY;
	return [x, y];
}

async function fetchJSON(url, opts = {}) {
	const res = await fetch(API_BASE + url, opts);
	if (!res.ok) {
		const t = await res.text().catch(() => "");
		throw new Error(`HTTP ${res.status}: ${t}`);
	}
	return await res.json();
}

function formatPx(n) {
	return Math.round(n) + " px";
}

// tìm node gần (ảnh px), trả id hoặc null
function findNearestNodeId(x, y, maxDist = 20) {
	let bestId = null,
		bestD = Infinity;
	for (const n of nodes) {
		const d = Math.hypot(n.x - x, n.y - y);
		if (d < bestD) {
			bestD = d;
			bestId = n.id;
		}
	}
	return bestD <= maxDist ? bestId : null;
}

// ---------- Load & Render ----------
async function loadMaps() {
	const data = await fetchJSON("/maps");
	maps = data.items || [];

	// mapSelect: liệt kê tất cả map
	mapSelect.innerHTML = maps
		.map((m) => `<option value="${m.id}">${m.name} (#${m.id})</option>`)
		.join("");

	if (maps.length) {
		await selectMap(maps[0].id);
	} else {
		mapImage.src = "";
		overlay.innerHTML = "";
	}
}

let currentFloor = null;

function ensureCurrentFloor() {
	if (currentFloor == null) {
		const v = parseInt(floorSelect?.value ?? "", 10);
		if (Number.isFinite(v)) currentFloor = v;
		else currentFloor = 1; // fallback
	}
	return currentFloor;
}

async function loadFloorsForCurrentMap() {
	if (!currentMap) return;

	// gom floor từ nodes & edges (nếu chưa có gì thì trả [1])
	const [ns, es] = await Promise.all([
		fetchJSON(`/nodes?map_id=${currentMap.id}`),
		fetchJSON(`/edges?map_id=${currentMap.id}`),
	]);

	const floors = new Set();
	(ns || []).forEach((n) => floors.add(n.floor ?? 1));
	(es || []).forEach((e) => floors.add(e.floor ?? 1));

	let list = Array.from(floors).sort((a, b) => Number(a) - Number(b));
	if (!list.length) list = [1];

	// render select
	floorSelect.innerHTML = list
		.map((f) => `<option value="${f}">${f}</option>`)
		.join("");

	// chọn mặc định: nếu có 1 thì lấy 1, không thì lấy phần tử đầu
	currentFloor = list.includes(1) ? 1 : list[0];
	floorSelect.value = String(currentFloor);
}

async function uploadMap() {
	upHint.textContent = "";

	const name = (upName.value || "").trim();
	const floor = (upFloor.value || "").trim(); // lưu dưới dạng string cho đơn giản
	const ppm = (upPPM.value || "").trim();
	const file = upFile.files && upFile.files[0];

	if (!name || !file) {
		upHint.textContent = "Vui lòng nhập tên bản đồ và chọn file ảnh.";
		return;
	}

	const fd = new FormData();
	fd.append("name", name);
	if (floor) fd.append("floor", floor);
	if (ppm) fd.append("pixels_per_meter", ppm);
	fd.append("file", file);

	try {
		// nếu backend là /maps thì đổi lại cho đúng
		const res = await fetch(API_BASE + "/maps", {
			method: "POST",
			body: fd,
		});
		if (!res.ok) throw new Error(await res.text());
		upHint.textContent = "Tải lên thành công. Đang làm mới danh sách…";
		upName.value = "";
		upFloor.value = "";
		upPPM.value = "";
		upFile.value = "";

		// reload
		await loadMaps();
		upHint.textContent = "Đã cập nhật danh sách bản đồ.";
	} catch (err) {
		console.error(err);
		upHint.textContent = "Lỗi upload: " + err.message;
	}
}

async function selectMap(mapId) {
	currentMap = await fetchJSON(`/maps/${mapId}`);
	mapSelect.value = currentMap.id;

	mapImage.src = currentMap.image_url;
	mapImage.onload = async () => {
		overlay.setAttribute(
			"viewBox",
			`0 0 ${currentMap.width} ${currentMap.height}`
		);
		overlay.setAttribute("width", mapImage.clientWidth);
		overlay.setAttribute("height", mapImage.clientHeight);

		await loadFloorsForCurrentMap();
		await loadNodesEdgesForFloor(currentFloor);
	};
}

async function loadNodesEdgesForFloor(floor) {
	if (!currentMap) return;
	nodes = await fetchJSON(`/nodes?map_id=${currentMap.id}&floor=${floor}`);
	edges = await fetchJSON(`/edges?map_id=${currentMap.id}&floor=${floor}`);
	await loadAliasesForNodes(nodes.map((n) => n.id));
	renderOverlay();
	renderLists();
}

async function loadAliasesForNodes(nodeIds) {
	aliasesByNode = {};
	await Promise.all(
		nodeIds.map(async (nid) => {
			const arr = await fetchJSON(`/aliases?node_id=${nid}`);
			aliasesByNode[nid] = arr;
		})
	);
}

function renderOverlay() {
	overlay.innerHTML = ""; // clear
	overlay.style.pointerEvents = mode === "idle" ? "none" : "auto";

	// edges
	for (const e of edges) {
		const d = e.polyline.map((p) => p.join(",")).join(" ");
		const line = document.createElementNS(
			"http://www.w3.org/2000/svg",
			"polyline"
		);
		line.setAttribute("points", d);
		line.setAttribute("class", "edge-line");
		overlay.appendChild(line);
	}

	// nodes
	for (const n of nodes) {
		const c = document.createElementNS(
			"http://www.w3.org/2000/svg",
			"circle"
		);
		c.setAttribute("cx", n.x);
		c.setAttribute("cy", n.y);
		c.setAttribute("r", 6);
		c.setAttribute("data-node-id", n.id);
		c.setAttribute(
			"class",
			"node-dot" + (n.is_landmark ? " landmark" : "")
		);
		c.style.pointerEvents = "auto";

		// CLICK: dùng single-click để chọn start hoặc kết thúc đường
		c.addEventListener("click", onNodeClick);
		// HOVER Tooltip
		c.addEventListener("mouseenter", onNodeEnter);
		c.addEventListener("mousemove", onNodeMove);
		c.addEventListener("mouseleave", onNodeLeave);

		overlay.appendChild(c);
	}

	// temp polyline (nếu có)
	if (tempPoints.length > 1) {
		tempLineEl = document.createElementNS(
			"http://www.w3.org/2000/svg",
			"polyline"
		);
		tempLineEl.setAttribute(
			"points",
			tempPoints.map((p) => p.join(",")).join(" ")
		);
		tempLineEl.setAttribute("class", "temp-line");
		overlay.appendChild(tempLineEl);
	}

	updateFinishBtn();
}

function renderLists() {
	nodeList.innerHTML = nodes
		.map((n) => {
			const aliases = (aliasesByNode[n.id] || [])
				.map(
					(a) => `
      <span class="alias-chip">${a.name}
        <button title="Xóa alias" data-action="del-alias" data-alias-id="${a.id}" data-node-id="${n.id}">×</button>
      </span>`
				)
				.join("");
			return `<div class="item" data-node="${n.id}">
      <div><b>#${n.id}</b> (${Math.round(n.x)}, ${Math.round(n.y)})${
				n.is_landmark ? " • landmark" : ""
			}</div>
      <div class="sub">Alias:</div>
      <div class="alias-list">${
			aliases || '<span class="small">— chưa có —</span>'
		}</div>
      <div class="alias-add">
        <input type="text" placeholder="Thêm alias..." data-input-alias="${
			n.id
		}">
        <button class="btn-mini" data-action="add-alias" data-node-id="${
			n.id
		}">Thêm</button>
      </div>
    </div>`;
		})
		.join("");

	edgeList.innerHTML = edges
		.map((e) => {
			return `<div class="item">
      <div><b>#${e.id}</b> ${e.start_node_id} → ${e.end_node_id}</div>
      <div class="sub">đoạn: ${e.polyline.length} • weight: ${formatPx(
				e.weight
			)}</div>
    </div>`;
		})
		.join("");
}

// ---------- Tooltip ----------
function tooltipShow(html, clientX, clientY) {
	tooltip.innerHTML = html;
	tooltip.style.display = "block";
	const r = board.getBoundingClientRect();
	let left = clientX - r.left + 12;
	let top = clientY - r.top + 12;
	// tránh tràn
	if (left + tooltip.offsetWidth > r.width - 8)
		left = r.width - tooltip.offsetWidth - 8;
	if (top + tooltip.offsetHeight > r.height - 8)
		top = r.height - tooltip.offsetHeight - 8;
	tooltip.style.left = left + "px";
	tooltip.style.top = top + "px";
}
function tooltipHide() {
	tooltip.style.display = "none";
}

function onNodeEnter(ev) {
	const nid = parseInt(ev.currentTarget.getAttribute("data-node-id"), 10);
	const aliases = (aliasesByNode[nid] || [])
		.slice(0, 3)
		.map((a) => a.name)
		.join(", ");
	const n = nodes.find((nn) => nn.id === nid);
	const html = `<b>Node #${nid}</b>${n.is_landmark ? " • landmark" : ""}<br>
                <span class="small">(${Math.round(n.x)}, ${Math.round(
		n.y
	)})</span><br>
                <span class="small">${
					aliases ? aliases : "— chưa có alias —"
				}</span>`;
	tooltipShow(html, ev.clientX, ev.clientY);
}
function onNodeMove(ev) {
	if (tooltip.style.display !== "block") return;
	tooltipShow(tooltip.innerHTML, ev.clientX, ev.clientY);
}
function onNodeLeave() {
	tooltipHide();
}

// ---------- Events ----------
overlay.addEventListener("click", async (ev) => {
	if (mode === "add-node") {
		const [x, y] = clientToImageXY(ev);
		const is_landmark = confirm(
			"Đặt điểm này là Landmark? OK = Có, Cancel = Không"
		);
		const body = {
			map_id: currentMap.id,
			x,
			y,
			is_landmark,
			floor: currentFloor,
		};
		const n = await fetchJSON("/nodes", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body),
		});
		// alias
		const alias = prompt("Nhập tên/alias cho điểm (bỏ qua nếu không):");
		if (alias && alias.trim()) {
			await fetchJSON("/aliases", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ node_id: n.id, name: alias.trim() }),
			});
		}
		await loadNodesEdgesForFloor(currentFloor);
	} else if (mode === "draw-edge") {
		// thêm điểm trung gian tự do
		if (!startNodeId) return; // yêu cầu chọn node bắt đầu trước
		const [x, y] = clientToImageXY(ev);
		tempPoints.push([x, y]);
		renderOverlay();
	}
});

function onNodeClick(ev) {
	if (mode !== "draw-edge") return;
	const el = ev.currentTarget;
	const nid = parseInt(el.getAttribute("data-node-id"), 10);
	if (!startNodeId) {
		// chọn start
		startNodeId = nid;
		const n = nodes.find((n) => n.id === nid);
		tempPoints = [[n.x, n.y]];
		el.classList.add("active");
		updateFinishBtn();
		renderOverlay();
	} else {
		// click vào node => kết thúc đường ở node đó
		finalizeEdge(nid);
	}
}

// ── Utils: chuẩn hoá polyline ──────────────────────────────────────────────
function _round(n, p = 1) {
	const m = Math.pow(10, p);
	return Math.round(n * m) / m;
}
function _samePt(a, b, eps = 0.01) {
	return Math.abs(a[0] - b[0]) <= eps && Math.abs(a[1] - b[1]) <= eps;
}
// bỏ điểm trùng liên tiếp + gộp điểm gần thẳng để bớt jitter
function normalizePolyline(pts, collinearEpsDeg = 5, distEps = 0.01) {
	if (!Array.isArray(pts) || pts.length < 2) return pts || [];

	// 1) bỏ trùng liên tiếp
	const uniq = [pts[0]];
	for (let i = 1; i < pts.length; i++) {
		if (!_samePt(pts[i], pts[i - 1], distEps)) uniq.push(pts[i]);
	}
	if (uniq.length < 2) return uniq;

	// 2) gộp gần thẳng (góc nhỏ)
	const out = [uniq[0]];
	for (let i = 1; i < uniq.length - 1; i++) {
		const A = out[out.length - 1];
		const B = uniq[i];
		const C = uniq[i + 1];

		const v1x = B[0] - A[0],
			v1y = B[1] - A[1];
		const v2x = C[0] - B[0],
			v2y = C[1] - B[1];
		const dot = v1x * v2x + v1y * v2y;
		const n1 = Math.hypot(v1x, v1y),
			n2 = Math.hypot(v2x, v2y);
		let keepMid = true;
		if (n1 > distEps && n2 > distEps) {
			const cos = Math.max(-1, Math.min(1, dot / (n1 * n2)));
			const ang = (Math.acos(cos) * 180) / Math.PI;
			if (ang <= collinearEpsDeg) keepMid = false; // gần thẳng -> bỏ B
		}
		if (keepMid) out.push(B);
	}
	out.push(uniq[uniq.length - 1]);

	// 3) làm tròn toạ độ cho đẹp
	return out.map(([x, y]) => [_round(x, 1), _round(y, 1)]);
}

async function finalizeEdge(targetNodeId) {
	try {
		if (!currentMap) throw new Error("Chưa chọn bản đồ.");
		if (!startNodeId || tempPoints.length < 1) return;

		const startNode = nodes.find((n) => n.id === startNodeId);
		const endNode = nodes.find((n) => n.id === targetNodeId);
		if (!endNode) return;

		// chống tự-nối
		if (endNode.id === startNodeId) {
			alert("Không thể nối một node với chính nó.");
			return;
		}

		// đảm bảo cùng tầng
		const floor = currentFloor ?? startNode?.floor ?? 1;

		// chốt điểm cuối là node đích
		const last = tempPoints[tempPoints.length - 1];
		if (!last || last[0] !== endNode.x || last[1] !== endNode.y) {
			tempPoints.push([endNode.x, endNode.y]);
		}

		// nếu chỉ có 1 điểm (lỡ click sai), tự thêm đoạn thẳng
		if (tempPoints.length < 2) {
			tempPoints = [
				[startNode.x, startNode.y],
				[endNode.x, endNode.y],
			];
		}

		// chuẩn hoá polyline (bỏ jitter/trùng, gộp gần thẳng, round toạ độ)
		const polyline = normalizePolyline(tempPoints);

		// body gửi lên backend
		const body = {
			map_id: currentMap.id,
			start_node_id: startNodeId,
			end_node_id: endNode.id,
			floor,
			polyline,
			bidirectional: true,
		};

		await fetchJSON("/edges", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body),
		});

		clearTemp();
		await loadNodesEdgesForFloor(floor);
	} catch (err) {
		alert(err.message || String(err));
	}
}

btnAddNode.addEventListener("click", () => setMode("add-node"));
btnDrawEdge.addEventListener("click", () => setMode("draw-edge"));
btnCancel.addEventListener("click", () => setMode("idle"));

btnFinishEdge.addEventListener("click", finishEdgeAuto);
function finishEdgeAuto() {
	if (!(mode === "draw-edge" && startNodeId && tempPoints.length >= 2))
		return;
	const last = tempPoints[tempPoints.length - 1];
	const nearId = findNearestNodeId(last[0], last[1], 20);
	if (!nearId || nearId === startNodeId) {
		alert(
			"Hãy click vào node đích (hoặc kéo điểm cuối gần node hơn) rồi nhấn Enter."
		);
		return;
	}
	finalizeEdge(nearId);
}

// Keyboard: Enter = finish, Esc = cancel, Z = undo
window.addEventListener("keydown", (e) => {
	if (mode !== "draw-edge") return;
	if (e.key === "Enter") {
		e.preventDefault();
		finishEdgeAuto();
	} else if (e.key === "Escape") {
		e.preventDefault();
		setMode("idle");
	} else if (e.key.toLowerCase() === "z") {
		// hoàn tác 1 điểm trung gian (giữ điểm đầu)
		if (tempPoints.length > 1) {
			tempPoints.pop();
			renderOverlay();
			updateFinishBtn();
		}
	}
});

reloadBtn.addEventListener("click", () => loadNodesEdgesForFloor(currentFloor));

mapSelect.addEventListener("change", async () => {
	await selectMap(parseInt(mapSelect.value, 10));
	setMode("idle");
});

// Alias add/remove (event delegation)
nodeList.addEventListener("click", async (e) => {
	const btn = e.target.closest("[data-action]");
	if (!btn) return;
	const action = btn.getAttribute("data-action");
	if (action === "add-alias") {
		const nodeId = parseInt(btn.getAttribute("data-node-id"), 10);
		const input = nodeList.querySelector(
			`input[data-input-alias="${nodeId}"]`
		);
		const val = (input?.value || "").trim();
		if (!val) return;
		try {
			await fetchJSON("/aliases", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ node_id: nodeId, name: val }),
			});
			input.value = "";
			// reload alias của node
			const arr = await fetchJSON(`/aliases?node_id=${nodeId}`);
			aliasesByNode[nodeId] = arr;
			renderLists();
		} catch (err) {
			alert(err.message);
		}
	} else if (action === "del-alias") {
		const aliasId = parseInt(btn.getAttribute("data-alias-id"), 10);
		const nodeId = parseInt(btn.getAttribute("data-node-id"), 10);
		if (!confirm("Xóa alias này?")) return;
		try {
			await fetchJSON(`/aliases/${aliasId}`, { method: "DELETE" });
			const arr = await fetchJSON(`/aliases?node_id=${nodeId}`);
			aliasesByNode[nodeId] = arr;
			renderLists();
		} catch (err) {
			alert(err.message);
		}
	}
});

floorSelect.addEventListener("change", async () => {
	const v = parseInt(floorSelect.value, 10);
	currentFloor = Number.isFinite(v) ? v : 1;
	await loadNodesEdgesForFloor(currentFloor);
	setMode("idle");
});

upBtn.addEventListener("click", uploadMap);

const btnClearAll = document.getElementById("clearAllBtn");

async function clearAllData() {
	if (!currentMap) return;
	// Xác nhận 2 bước: gõ tên map hoặc "XOA"
	const warn = `Bạn sắp XÓA TOÀN BỘ Nodes/Aliases/Edges của map: "${currentMap.name}" (#${currentMap.id}).\n\nGõ chính xác tên map hoặc gõ "XOA" để tiếp tục:`;
	const input = prompt(warn, "");
	if (input === null) return; // user cancel

	if (input !== currentMap.name && input.toUpperCase() !== "XOA") {
		alert("Không khớp. Hủy thao tác.");
		return;
	}

	try {
		const res = await fetchJSON("/admin/clear-map", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ map_id: currentMap.id, delete_map: false }),
		});
		await loadNodesEdgesForFloor(currentFloor);
		alert(
			`Đã xóa: ${res.deleted.nodes} nodes, ${res.deleted.aliases} aliases, ${res.deleted.edges} edges.`
		);
	} catch (err) {
		alert("Lỗi khi xóa: " + err.message);
	}
}

addFloorBtn.addEventListener("click", async () => {
	if (!currentMap) return;
	const val = prompt("Nhập số tầng mới (ví dụ: 2, 3, 4...):", "");
	if (val == null) return;

	const n = parseInt(val, 10);
	if (!Number.isFinite(n)) {
		alert("Giá trị không hợp lệ.");
		return;
	}

	// nếu đã tồn tại thì chỉ cần chọn
	const exists = Array.from(floorSelect.options).some(
		(o) => parseInt(o.value, 10) === n
	);
	if (!exists) {
		const opt = document.createElement("option");
		opt.value = String(n);
		opt.textContent = String(n);
		// chèn theo thứ tự
		const opts = Array.from(floorSelect.options);
		const insertAt = opts.findIndex((o) => parseInt(o.value, 10) > n);
		if (insertAt >= 0) floorSelect.add(opt, opts[insertAt]);
		else floorSelect.add(opt);
	}

	currentFloor = n;
	floorSelect.value = String(n);

	// Tầng mới chưa có dữ liệu → load rỗng
	await loadNodesEdgesForFloor(currentFloor);
	setMode("idle");
});

btnClearAll.addEventListener("click", clearAllData);
// Init
loadMaps().catch((err) => alert(err.message));
