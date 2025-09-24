const API_BASE = "";

let maps = [];
let currentMap = null;
let nodes = [];
let aliasesByNode = {}; // { nodeId: Alias[] }

let myPos = null; // [x,y]
let placingPos = false;
let routeEl = null;

const mapSelect = document.getElementById("mapSelect");
const mapImage = document.getElementById("mapImage");
const overlay = document.getElementById("overlay");
const board = document.getElementById("board");
const tooltip = document.getElementById("tooltip");

const insList = document.getElementById("insList");
const suggestList = document.getElementById("suggestList");
const queryEl = document.getElementById("query");
const setPosBtn = document.getElementById("setPosBtn");
const goBtn = document.getElementById("goBtn");
const hintBadge = document.getElementById("hintBadge");
const scaleInput = document.getElementById("scaleInput");

// --------- Scale (px -> m) ----------
function getPixelsPerMeter() {
	const v = parseFloat(scaleInput.value);
	return isFinite(v) && v > 0 ? v : 100;
}
function fmtMeters(px) {
	const ppm = getPixelsPerMeter();
	const m = px / ppm;
	// làm tròn dễ đọc
	if (m >= 100) return `${Math.round(m)} m`;
	if (m >= 10) return `${m.toFixed(1)} m`;
	return `${m.toFixed(1)} m`;
}
function setHint(txt) {
	hintBadge.textContent = txt;
}

// --------- Helpers ----------
async function fetchJSON(url, opts = {}) {
	const res = await fetch(API_BASE + url, opts);
	if (!res.ok) {
		const t = await res.text().catch(() => "");
		throw new Error(`HTTP ${res.status}: ${t}`);
	}
	return await res.json();
}
function clientToImageXY(ev) {
	const rect = mapImage.getBoundingClientRect();
	const scaleX = currentMap.width / rect.width;
	const scaleY = currentMap.height / rect.height;
	const x = (ev.clientX - rect.left) * scaleX;
	const y = (ev.clientY - rect.top) * scaleY;
	return [x, y];
}

// --------- Load ----------
async function loadMaps() {
	const data = await fetchJSON("/maps");
	maps = data.items || [];
	mapSelect.innerHTML = maps
		.map((m) => `<option value="${m.id}">${m.name} (#${m.id})</option>`)
		.join("");
	if (maps.length > 0) await selectMap(maps[0].id);
}
async function selectMap(mapId) {
	currentMap = await fetchJSON(`/maps/${mapId}`);
	mapSelect.value = currentMap.id;

	// Nếu backend có pixels_per_meter thì tự set
	if (
		typeof currentMap.pixels_per_meter === "number" &&
		currentMap.pixels_per_meter > 0
	) {
		scaleInput.value = String(Math.round(currentMap.pixels_per_meter));
	}

	mapImage.src = currentMap.image_url;
	mapImage.onload = async () => {
		overlay.setAttribute(
			"viewBox",
			`0 0 ${currentMap.width} ${currentMap.height}`
		);
		overlay.setAttribute("width", mapImage.clientWidth);
		overlay.setAttribute("height", mapImage.clientHeight);
		await loadNodes(); // không load edges
		renderAll();
	};
}
async function loadNodes() {
	nodes = await fetchJSON(`/nodes?map_id=${currentMap.id}`);
	// load alias cho tooltip (đơn giản, như Editor)
	aliasesByNode = {};
	await Promise.all(
		nodes.map(async (n) => {
			const arr = await fetchJSON(`/aliases?node_id=${n.id}`);
			aliasesByNode[n.id] = arr;
		})
	);
}

// --------- Render ----------
function renderAll() {
	overlay.innerHTML = ""; // clear

	// ❌ Không vẽ edges nền
	// ✅ Vẽ nodes để hover/tooltip
	for (const n of nodes) {
		const c = document.createElementNS(
			"http://www.w3.org/2000/svg",
			"circle"
		);
		c.setAttribute("cx", n.x);
		c.setAttribute("cy", n.y);
		c.setAttribute("r", 5);
		c.setAttribute(
			"class",
			"node-dot" + (n.is_landmark ? " landmark" : "")
		);
		c.style.pointerEvents = "auto";
		c.dataset.nodeId = n.id;

		c.addEventListener("mouseenter", onNodeEnter);
		c.addEventListener("mousemove", onNodeMove);
		c.addEventListener("mouseleave", onNodeLeave);

		overlay.appendChild(c);
	}

	// vị trí của tôi
	if (myPos) {
		const me = document.createElementNS(
			"http://www.w3.org/2000/svg",
			"circle"
		);
		me.setAttribute("cx", myPos[0]);
		me.setAttribute("cy", myPos[1]);
		me.setAttribute("r", 6);
		me.setAttribute("class", "mypos");
		overlay.appendChild(me);
	}
}

function drawRoute(polyline) {
	if (routeEl) routeEl.remove();
	routeEl = document.createElementNS(
		"http://www.w3.org/2000/svg",
		"polyline"
	);
	routeEl.setAttribute("points", polyline.map((p) => p.join(",")).join(" "));
	routeEl.setAttribute("class", "route-line");
	overlay.appendChild(routeEl);
}

// --------- Tooltip ----------
function tooltipShow(html, clientX, clientY) {
	tooltip.innerHTML = html;
	tooltip.style.display = "block";
	const r = board.getBoundingClientRect();
	let left = clientX - r.left + 12;
	let top = clientY - r.top + 12;
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
	const nid = parseInt(ev.currentTarget.dataset.nodeId, 10);
	const n = nodes.find((x) => x.id === nid);
	const als = (aliasesByNode[nid] || [])
		.slice(0, 3)
		.map((a) => a.name)
		.join(", ");
	const html = `<b>Node #${nid}</b>${n.is_landmark ? " • landmark" : ""}<br>
                <span class="small">(${Math.round(n.x)}, ${Math.round(
		n.y
	)})</span><br>
                <span class="small">${als || "— chưa có alias —"}</span>`;
	tooltipShow(html, ev.clientX, ev.clientY);
}
function onNodeMove(ev) {
	if (tooltip.style.display !== "block") return;
	tooltipShow(tooltip.innerHTML, ev.clientX, ev.clientY);
}
function onNodeLeave() {
	tooltipHide();
}

// --------- Instructions (px -> m) ----------
function showInstructions(items) {
	// đổi "Đi thẳng N px" -> "Đi thẳng Xm"
	insList.innerHTML = items
		.map((ins, idx) => {
			let text = ins.text;
			// nếu là mẫu "Đi thẳng {N} px" ở đầu câu, thay bằng mét theo distance_px
			text = text.replace(
				/(Đi thẳng)\s+\d+\s*px/i,
				`$1 ${fmtMeters(ins.distance_px)}`
			);
			// subline: hiển thị distance theo m
			const sub = `${ins.kind} • ~${fmtMeters(ins.distance_px)}`;
			return `<div class="item"><div><b>${
				idx + 1
			}.</b> ${text}</div><div class="sub">${sub}</div></div>`;
		})
		.join("");
}

// --------- Events ----------
overlay.addEventListener("click", (ev) => {
	if (!placingPos) return;
	myPos = clientToImageXY(ev);
	placingPos = false;
	setPosBtn.textContent = "Đặt vị trí của tôi";
	setHint(
		`Đã đặt vị trí tại (${Math.round(myPos[0])}, ${Math.round(myPos[1])})`
	);
	renderAll();
});

setPosBtn.addEventListener("click", () => {
	placingPos = !placingPos;
	setPosBtn.textContent = placingPos
		? "Bấm lên bản đồ..."
		: "Đặt vị trí của tôi";
	setHint(
		placingPos
			? "Bấm lên bản đồ để chọn vị trí của bạn"
			: "Đã thoát chế độ đặt vị trí"
	);
});

goBtn.addEventListener("click", async () => {
	suggestList.innerHTML = "";
	insList.innerHTML = "";
	if (!queryEl.value.trim()) {
		setHint("Nhập câu hỏi trước nhé");
		return;
	}

	const payload = { map_id: currentMap.id, q: queryEl.value.trim() };
	if (myPos) {
		payload.cx = myPos[0];
		payload.cy = myPos[1];
	}

	try {
		const res = await fetchJSON("/route", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(payload),
		});
		drawRoute(res.polyline);
		showInstructions(res.instructions);
		setHint(`Tổng quãng ~ ${fmtMeters(res.length_px)}`);
	} catch (err) {
		setHint("Không tìm được đường: " + err.message);
		// gợi ý từ khóa alias
		try {
			const parts = queryEl.value
				.toLowerCase()
				.split(/\s+|->|đến|tới|tu|từ|,|\./)
				.filter(Boolean);
			const uniq = [...new Set(parts)].filter((w) => w.length >= 2);
			const sug = new Set();
			for (const p of uniq) {
				const s = await fetchJSON(
					`/aliases/search?q=${encodeURIComponent(p)}`
				);
				s.forEach((it) =>
					sug.add(`${p} → #node ${it.node_id} (${it.name})`)
				);
			}
			suggestList.innerHTML = [...sug]
				.slice(0, 8)
				.map((s) => `<div class="item">${s}</div>`)
				.join("");
		} catch (_) {}
	}
});

mapSelect.addEventListener("change", async () => {
	await selectMap(parseInt(mapSelect.value, 10));
	myPos = null;
	renderAll();
});

// đổi scale -> cập nhật lại hiển thị (chỉ ảnh hưởng text, không cần reload)
scaleInput.addEventListener("change", () => {
	// re-render instruction nếu có
	const cards = insList.querySelectorAll(".item");
	if (cards.length) {
		// trigger lại nút Go để tính lại format m
		goBtn.click();
	}
});

// Init
loadMaps().catch((err) => setHint(err.message));
