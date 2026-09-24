const COLOR_STOPS = [
  { t: 0.0, color: [49, 100, 175] },
  { t: 0.5, color: [247, 234, 173] },
  { t: 1.0, color: [178, 40, 33] },
];

function colorForValue(value, min, max) {
  if (max === min) {
    return [150, 150, 150];
  }

  const t = Math.max(0, Math.min(1, (value - min) / (max - min)));

  let lower = COLOR_STOPS[0];
  let upper = COLOR_STOPS[COLOR_STOPS.length - 1];

  for (let i = 0; i < COLOR_STOPS.length - 1; i += 1) {
    if (t >= COLOR_STOPS[i].t && t <= COLOR_STOPS[i + 1].t) {
      lower = COLOR_STOPS[i];
      upper = COLOR_STOPS[i + 1];
      break;
    }
  }

  const span = upper.t - lower.t || 1;
  const localT = (t - lower.t) / span;

  return lower.color.map((channel, i) =>
    Math.round(channel + (upper.color[i] - channel) * localT)
  );
}

function temperatureToColor(value, min, max) {
  const [r, g, b] = colorForValue(value, min, max);
  return `rgb(${r},${g},${b})`;
}

// Gaussian kernel density estimate over a small set of observed
// values (e.g. one value per municipality within a zone) - turns
// discrete observations into the smooth distribution curve the
// professor asked for (like a normal-distribution plot), rather than
// a discrete-bar histogram.
function gaussianKernelDensity(values, gridSize = 120) {
  const n = values.length;
  const mean = values.reduce((sum, v) => sum + v, 0) / n;
  const variance =
    values.reduce((sum, v) => sum + (v - mean) ** 2, 0) / n;
  const stdDev = Math.sqrt(variance) || 1;

  // Silverman's rule of thumb for kernel bandwidth.
  const bandwidth = 1.06 * stdDev * Math.pow(n, -1 / 5) || 1;

  // Plain loops, not Math.min(...values)/Math.max(...values): spreading
  // a per-pixel array (up to ~147k values for Castilla y Leon) into a
  // function call exceeds the JS engine's argument-count limit
  // (~65k in Chromium) and throws silently, which is why only the
  // smaller zones (e.g. Extremadura's 62,531 pixels) ever rendered.
  let dataMin = values[0];
  let dataMax = values[0];
  for (let i = 1; i < values.length; i += 1) {
    if (values[i] < dataMin) dataMin = values[i];
    if (values[i] > dataMax) dataMax = values[i];
  }
  const pad = (dataMax - dataMin) * 0.25 || bandwidth * 3;
  const gridMin = dataMin - pad;
  const gridMax = dataMax + pad;

  const grid = [];
  for (let i = 0; i < gridSize; i += 1) {
    const x = gridMin + ((gridMax - gridMin) * i) / (gridSize - 1);
    const density =
      values.reduce((sum, v) => {
        const u = (x - v) / bandwidth;
        return sum + Math.exp(-0.5 * u * u);
      }, 0) / (n * bandwidth * Math.sqrt(2 * Math.PI));
    grid.push({ x, density });
  }

  return grid;
}

// Draws a smooth distribution curve (Gaussian KDE) for a set of
// observed values, with a crosshair and value-reading tooltip on
// hover/keyboard nav. "values" is that zone's flattened per-pixel
// index grid (up to ~147k values for Castilla y Leon).
function drawDistributionChart(svg, values, options = {}) {
  svg.innerHTML = "";

  if (!values || values.length === 0) {
    return;
  }

  const width = 300;
  const height = 160;
  const padding = { top: 10, right: 12, bottom: 34, left: 24 };

  const grid = gaussianKernelDensity(values);
  const maxDensity = Math.max(...grid.map((p) => p.density)) || 1;

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const gridMinX = grid[0].x;
  const gridMaxX = grid[grid.length - 1].x;

  const xFor = (x) =>
    padding.left + ((x - gridMinX) / (gridMaxX - gridMinX)) * plotWidth;

  const yFor = (density) =>
    padding.top + plotHeight - (density / maxDensity) * plotHeight;

  const ns = "http://www.w3.org/2000/svg";

  const axis = document.createElementNS(ns, "line");
  axis.setAttribute("x1", padding.left);
  axis.setAttribute("y1", height - padding.bottom);
  axis.setAttribute("x2", width - padding.right);
  axis.setAttribute("y2", height - padding.bottom);
  axis.setAttribute("stroke", "#c7ccd3");
  svg.appendChild(axis);

  const xAxisTitle = document.createElementNS(ns, "text");
  xAxisTitle.setAttribute("x", padding.left + plotWidth / 2);
  xAxisTitle.setAttribute("y", height - 4);
  xAxisTitle.setAttribute("text-anchor", "middle");
  xAxisTitle.setAttribute("font-size", "8.5");
  xAxisTitle.setAttribute("fill", "#5b6675");
  xAxisTitle.textContent = options.xLabel || "Value";
  svg.appendChild(xAxisTitle);

  const yAxisTitle = document.createElementNS(ns, "text");
  yAxisTitle.setAttribute("x", 0);
  yAxisTitle.setAttribute("y", 0);
  yAxisTitle.setAttribute("text-anchor", "middle");
  yAxisTitle.setAttribute("font-size", "8.5");
  yAxisTitle.setAttribute("fill", "#5b6675");
  yAxisTitle.setAttribute(
    "transform",
    `translate(9, ${padding.top + plotHeight / 2}) rotate(-90)`
  );
  yAxisTitle.textContent = options.yLabel || "Density";
  svg.appendChild(yAxisTitle);

  const curvePoints = grid
    .map((p) => `${xFor(p.x)},${yFor(p.density)}`)
    .join(" ");

  const areaPolygon =
    `${padding.left},${height - padding.bottom} ${curvePoints} ` +
    `${width - padding.right},${height - padding.bottom}`;

  const area = document.createElementNS(ns, "polygon");
  area.setAttribute("points", areaPolygon);
  area.setAttribute("fill", "#2f6fb2");
  area.setAttribute("fill-opacity", "0.12");
  svg.appendChild(area);

  const curve = document.createElementNS(ns, "polyline");
  curve.setAttribute("points", curvePoints);
  curve.setAttribute("fill", "none");
  curve.setAttribute("stroke", "#2f6fb2");
  curve.setAttribute("stroke-width", "2.5");
  svg.appendChild(curve);

  const crosshair = document.createElementNS(ns, "line");
  crosshair.setAttribute("y1", padding.top);
  crosshair.setAttribute("y2", height - padding.bottom);
  crosshair.setAttribute("stroke", "#9aa3af");
  crosshair.setAttribute("stroke-width", "1");
  crosshair.setAttribute("visibility", "hidden");
  svg.appendChild(crosshair);

  const highlight = document.createElementNS(ns, "circle");
  highlight.setAttribute("r", "4.5");
  highlight.setAttribute("fill", "#2f6fb2");
  highlight.setAttribute("stroke", "#ffffff");
  highlight.setAttribute("stroke-width", "1.5");
  highlight.setAttribute("visibility", "hidden");
  svg.appendChild(highlight);

  const tooltipGroup = document.createElementNS(ns, "g");
  tooltipGroup.setAttribute("visibility", "hidden");

  const tooltipBg = document.createElementNS(ns, "rect");
  tooltipBg.setAttribute("rx", "3");
  tooltipBg.setAttribute("fill", "#1c2430");
  tooltipGroup.appendChild(tooltipBg);

  const tooltipValue = document.createElementNS(ns, "text");
  tooltipValue.setAttribute("font-size", "11");
  tooltipValue.setAttribute("font-weight", "700");
  tooltipValue.setAttribute("fill", "#ffffff");
  tooltipValue.setAttribute("text-anchor", "middle");
  tooltipGroup.appendChild(tooltipValue);

  const tooltipLabel = document.createElementNS(ns, "text");
  tooltipLabel.setAttribute("font-size", "8.5");
  tooltipLabel.setAttribute("fill", "#c7ccd3");
  tooltipLabel.setAttribute("text-anchor", "middle");
  tooltipGroup.appendChild(tooltipLabel);

  svg.appendChild(tooltipGroup);

  const hitArea = document.createElementNS(ns, "rect");
  hitArea.setAttribute("x", padding.left);
  hitArea.setAttribute("y", padding.top);
  hitArea.setAttribute("width", plotWidth);
  hitArea.setAttribute("height", plotHeight);
  hitArea.setAttribute("fill", "transparent");
  svg.appendChild(hitArea);

  const unit = options.unit || "";

  const nearestGridIndexForDataX = (x) => {
    let closest = 0;
    let closestDist = Infinity;
    grid.forEach((p, i) => {
      const d = Math.abs(p.x - x);
      if (d < closestDist) {
        closestDist = d;
        closest = i;
      }
    });
    return closest;
  };

  const updateAt = (gridIndex) => {
    const clamped = Math.max(0, Math.min(grid.length - 1, gridIndex));
    const point = grid[clamped];
    const px = xFor(point.x);
    const py = yFor(point.density);

    crosshair.setAttribute("x1", px);
    crosshair.setAttribute("x2", px);
    crosshair.setAttribute("visibility", "visible");

    highlight.setAttribute("cx", px);
    highlight.setAttribute("cy", py);
    highlight.setAttribute("visibility", "visible");

    const valueText = `${point.x.toFixed(1)}${unit}`;
    const labelText = "estimated density";

    tooltipValue.textContent = valueText;
    tooltipValue.setAttribute("x", 0);
    tooltipValue.setAttribute("y", 14);

    tooltipLabel.textContent = labelText;
    tooltipLabel.setAttribute("x", 0);
    tooltipLabel.setAttribute("y", 25);

    const boxWidth =
      Math.max(valueText.length, labelText.length) * 6 + 12;
    const boxHeight = 32;

    tooltipBg.setAttribute("x", -boxWidth / 2);
    tooltipBg.setAttribute("y", -2);
    tooltipBg.setAttribute("width", boxWidth);
    tooltipBg.setAttribute("height", boxHeight);

    let tooltipY = py - boxHeight - 6;
    if (tooltipY < 0) {
      tooltipY = py + 10;
    }

    const tooltipX = Math.max(
      boxWidth / 2,
      Math.min(width - boxWidth / 2, px)
    );

    tooltipGroup.setAttribute(
      "transform",
      `translate(${tooltipX}, ${tooltipY})`
    );
    tooltipGroup.setAttribute("visibility", "visible");
  };

  const hide = () => {
    crosshair.setAttribute("visibility", "hidden");
    highlight.setAttribute("visibility", "hidden");
    tooltipGroup.setAttribute("visibility", "hidden");
  };

  const nearestGridIndexForClientX = (clientX) => {
    const rect = svg.getBoundingClientRect();
    const svgX = ((clientX - rect.left) / rect.width) * width;
    const relative = (svgX - padding.left) / plotWidth;
    const dataX = gridMinX + relative * (gridMaxX - gridMinX);
    return nearestGridIndexForDataX(dataX);
  };

  hitArea.addEventListener("pointermove", (event) => {
    updateAt(nearestGridIndexForClientX(event.clientX));
  });
  hitArea.addEventListener("pointerleave", hide);

  svg.setAttribute("tabindex", "0");
  svg.setAttribute("role", "img");
  svg.setAttribute(
    "aria-label",
    "Distribution of values for the selected index in the zone, use " +
    "the arrow keys to navigate"
  );

  let focusedIndex = Math.floor(grid.length / 2);
  svg.addEventListener("focus", () => updateAt(focusedIndex));
  svg.addEventListener("blur", hide);
  svg.addEventListener("keydown", (event) => {
    const step = Math.max(1, Math.floor(grid.length / 20));
    if (event.key === "ArrowRight") {
      focusedIndex = Math.min(grid.length - 1, focusedIndex + step);
      updateAt(focusedIndex);
      event.preventDefault();
    } else if (event.key === "ArrowLeft") {
      focusedIndex = Math.max(0, focusedIndex - step);
      updateAt(focusedIndex);
      event.preventDefault();
    }
  });
}

// The 4 crop names are confirmed (docs/04). Values must match the
// English crop keys used in indices_catalog.json's "crops" field
// (src/indices_catalog.py's CROP_COLUMNS mapping).
const CULTURAS = ["Grapevine", "Olive", "Almond", "Cherry"];

// Mirrors config/climate.toml's [future] section (periods/scenarios).
// Only "historical" and "2041-2070" are actually covered by the
// professor's ensemble1 delivery today (see docs/04 Section 2.1) -
// the other periods are shown so the UI is ready for future
// deliveries, and simply report "not delivered yet" until then.
const FUTURE_PERIODS = ["2041-2070", "2071-2100"];
const FUTURE_SCENARIOS = [
  { value: "ssp126", label: "SSP1-2.6 (moderate)" },
  { value: "ssp585", label: "SSP5-8.5 (severe)" },
];

const SELECT_CROP_PROMPT = "Select a Crop, Index, Period and SSP above to view zone data.";

let map = null;
let zonesLayer = null;
let indexOverlayGroup = null;
let currentLegend = null;
let zoneFeaturesBySlug = {};
let selectedZoneSlug = null;

let indicesCatalog = null; // /api/indices response, kept in memory
let currentIndexCode = null;
let currentIndexData = null; // last successful /api/pilot/zones/index/... response
let currentEpochLabel = null; // human-readable label for the active period/SSP

function initMap() {
  map = L.map("map");

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "© OpenStreetMap contributors",
  }).addTo(map);

  indexOverlayGroup = L.layerGroup().addTo(map);
}

// One shared gradient bar (global_min -> global_max), not a per-zone
// legend, per the confirmed decision to use a single color scale
// across all 5 zones.
function buildIndexLegend(min, max, title) {
  const legend = L.control({ position: "bottomright" });

  legend.onAdd = () => {
    const div = L.DomUtil.create("div", "info-legend");
    const [r0, g0, b0] = colorForValue(min, min, max);
    const [r1, g1, b1] = colorForValue((min + max) / 2, min, max);
    const [r2, g2, b2] = colorForValue(max, min, max);
    const gradient =
      `linear-gradient(to right, rgb(${r0},${g0},${b0}), ` +
      `rgb(${r1},${g1},${b1}), rgb(${r2},${g2},${b2}))`;

    div.innerHTML = `
      <div id="legend">
        <strong>${title}</strong>
        <div id="legend-gradient-bar" style="background:${gradient}"></div>
        <div id="legend-gradient-labels">
          <span>${min.toFixed(1)}</span>
          <span>${max.toFixed(1)}</span>
        </div>
        <div id="legend-caption">
          ~1km resolution, smoothed rendering
        </div>
      </div>`;

    return div;
  };

  return legend;
}

function pendingZoneStyle() {
  return {
    fillColor: "#c7ccd3",
    fillOpacity: 0.4,
    weight: 1.5,
    color: "#9aa3af",
    dashArray: "4 3",
  };
}

function activeZoneStyle() {
  // The raster heatmap overlay (L.imageOverlay) provides the actual
  // color; the polygon here only supplies the boundary stroke and
  // the click hit-area.
  return {
    fillColor: "#000000",
    fillOpacity: 0,
    weight: 1.5,
    color: "#3a4250",
  };
}

async function loadZones() {
  let featureCollection;
  try {
    const response = await fetch("/api/pilot/zones");
    if (!response.ok) {
      throw new Error(await response.text());
    }
    featureCollection = await response.json();
  } catch (err) {
    document.getElementById("banner-subtitle").innerHTML =
      "No zone has been built yet. Run " +
      "<code>python -m scripts.build_zone_overview</code> locally " +
      "and restart the API.";
    return;
  }

  if (!featureCollection.features || featureCollection.features.length === 0) {
    document.getElementById("banner-subtitle").innerHTML =
      "No zone has been built yet. Run " +
      "<code>python -m scripts.build_zone_overview</code> locally " +
      "and restart the API.";
    return;
  }

  zoneFeaturesBySlug = {};
  featureCollection.features.forEach((feature) => {
    zoneFeaturesBySlug[feature.properties.slug] = feature;
  });

  zonesLayer = L.geoJSON(featureCollection, {
    style: pendingZoneStyle,
    onEachFeature: (feature, layer) => {
      layer.bindTooltip(feature.properties.label);
      layer.on("click", (event) => onZoneClick(feature.properties.slug, event.latlng));
    },
  }).addTo(map);

  map.fitBounds(zonesLayer.getBounds(), { padding: [16, 16] });
}

function showBannerWarning(message) {
  const el = document.getElementById("banner-warning");
  el.textContent = message;
  el.hidden = false;
}

function hideBannerWarning() {
  document.getElementById("banner-warning").hidden = true;
}

function clearIndexView(message) {
  currentIndexData = null;
  indexOverlayGroup.clearLayers();

  if (zonesLayer) {
    zonesLayer.setStyle(pendingZoneStyle);
  }
  if (currentLegend) {
    map.removeControl(currentLegend);
    currentLegend = null;
  }

  document.getElementById("banner-subtitle").textContent = SELECT_CROP_PROMPT;

  if (message) {
    showBannerWarning(message);
  } else {
    hideBannerWarning();
  }

  renderZonePanel();
}

// Paints one zone's pixel grid onto a canvas and returns a data URL,
// using the shared global min/max so colors are comparable across
// all 5 zones. Null cells (outside the zone polygon, or nodata) stay
// fully transparent.
function renderZoneCanvasDataUrl(zoneGrid, globalMin, globalMax) {
  const canvas = document.createElement("canvas");
  canvas.width = zoneGrid.width;
  canvas.height = zoneGrid.height;
  const ctx = canvas.getContext("2d");
  const imageData = ctx.createImageData(zoneGrid.width, zoneGrid.height);

  let offset = 0;
  for (let row = 0; row < zoneGrid.height; row += 1) {
    const rowValues = zoneGrid.values[row];
    for (let col = 0; col < zoneGrid.width; col += 1) {
      const value = rowValues[col];
      if (value === null) {
        imageData.data[offset + 3] = 0;
      } else {
        const [r, g, b] = colorForValue(value, globalMin, globalMax);
        imageData.data[offset] = r;
        imageData.data[offset + 1] = g;
        imageData.data[offset + 2] = b;
        imageData.data[offset + 3] = 235;
      }
      offset += 4;
    }
  }

  ctx.putImageData(imageData, 0, 0);
  return canvas.toDataURL();
}

function renderIndexZones(data, legendTitle) {
  indexOverlayGroup.clearLayers();

  data.zones.forEach((zoneGrid) => {
    const dataUrl = renderZoneCanvasDataUrl(
      zoneGrid, data.global_min, data.global_max
    );
    const bounds = L.latLngBounds(
      [zoneGrid.bounds.south, zoneGrid.bounds.west],
      [zoneGrid.bounds.north, zoneGrid.bounds.east]
    );
    L.imageOverlay(dataUrl, bounds, { opacity: 0.85 }).addTo(indexOverlayGroup);
  });

  if (zonesLayer) {
    zonesLayer.setStyle(activeZoneStyle);
  }

  if (currentLegend) {
    map.removeControl(currentLegend);
  }
  currentLegend = buildIndexLegend(data.global_min, data.global_max, legendTitle);
  currentLegend.addTo(map);

  hideBannerWarning();
  document.getElementById("banner-subtitle").textContent =
    "Click a zone for its value distribution, or click a point on the map for its exact value.";
}

function showDistribution(values, caption) {
  document.getElementById("panel-distribution-caption").textContent = caption;
  document.getElementById("panel-distribution-wrapper").hidden = false;
  drawDistributionChart(
    document.getElementById("panel-distribution-chart"),
    values,
    { unit: "" }
  );
}

// Redraws the side panel for the currently selected zone (if any),
// using currentIndexData - called both on zone click and whenever
// the active index data changes (so an open panel stays in sync).
function renderZonePanel() {
  const feature = selectedZoneSlug ? zoneFeaturesBySlug[selectedZoneSlug] : null;

  if (!feature) {
    document.getElementById("panel-empty").hidden = false;
    document.getElementById("panel-content").hidden = true;
    return;
  }

  document.getElementById("panel-empty").hidden = true;
  document.getElementById("panel-content").hidden = false;
  document.getElementById("panel-name").textContent = feature.properties.label;

  const annualEl = document.getElementById("panel-annual");
  const pendingEl = document.getElementById("panel-pending");
  const distWrapper = document.getElementById("panel-distribution-wrapper");

  const zoneGrid = currentIndexData
    ? currentIndexData.zones.find((z) => z.slug === selectedZoneSlug)
    : null;

  if (!zoneGrid) {
    annualEl.textContent = "";
    pendingEl.hidden = false;
    pendingEl.textContent = SELECT_CROP_PROMPT;
    distWrapper.hidden = true;
    return;
  }

  pendingEl.hidden = true;
  annualEl.textContent =
    `Mean: ${zoneGrid.mean} · Min: ${zoneGrid.min} · Max: ${zoneGrid.max} ` +
    `(${currentEpochLabel})`;

  const values = [];
  zoneGrid.values.forEach((row) => {
    row.forEach((v) => {
      if (v !== null) {
        values.push(v);
      }
    });
  });

  showDistribution(
    values,
    `Distribution of ${currentIndexCode} across all pixels in the zone (${currentEpochLabel})`
  );
}

async function onZoneClick(slug, latlng) {
  selectedZoneSlug = slug;
  renderZonePanel();

  if (!currentIndexCode || !currentIndexData) {
    return;
  }

  const epochPath = getEpochPath();
  if (epochPath === null) {
    return;
  }

  try {
    const response = await fetch(
      `/api/pilot/${slug}/index/${currentIndexCode}${epochPath}/point` +
      `?lat=${latlng.lat}&lon=${latlng.lng}`
    );
    if (!response.ok) {
      return;
    }
    const point = await response.json();
    L.popup()
      .setLatLng(latlng)
      .setContent(`<strong>${currentIndexCode}</strong>: ${point.value}`)
      .openOn(map);
  } catch (err) {
    // Point-query is a convenience on top of the heatmap; silently
    // skip the popup if it fails rather than interrupting the click.
  }
}

// Returns "" for historical, or "/{scenario}/{period}" for a future
// slice - null if the current period/SSP selection is incomplete.
function getEpochPath() {
  const period = document.getElementById("period-select").value;

  if (period === "historical") {
    return "";
  }

  const scenario = document.getElementById("ssp-select").value;
  if (!scenario) {
    return null;
  }

  return `/${scenario}/${period}`;
}

function getEpochLabel() {
  const period = document.getElementById("period-select").value;

  if (period === "historical") {
    return "Historical (1981-2010)";
  }

  const scenario = document.getElementById("ssp-select").value;
  const scenarioMeta = FUTURE_SCENARIOS.find((s) => s.value === scenario);
  return `${scenarioMeta ? scenarioMeta.label : scenario} · ${period}`;
}

function showFormulaBox(entry) {
  document.getElementById("index-formula-name").textContent =
    `${entry.category} — ${entry.name}`;
  document.getElementById("index-formula-value").textContent =
    `Formula: ${entry.formula}`;
  document.getElementById("index-formula-reference").textContent =
    entry.reference && entry.reference !== "—"
      ? `Reference: ${entry.reference}`
      : "";
  document.getElementById("index-formula-box").hidden = false;
}

function hideFormulaBox() {
  document.getElementById("index-formula-box").hidden = true;
}

async function updateIndexView() {
  const indexSelect = document.getElementById("indice-select");
  currentIndexCode = indexSelect.value || null;

  if (!currentIndexCode) {
    hideFormulaBox();
    clearIndexView(null);
    return;
  }

  showFormulaBox(indicesCatalog.indices[currentIndexCode]);

  const epochPath = getEpochPath();
  if (epochPath === null) {
    clearIndexView(null);
    document.getElementById("banner-subtitle").textContent =
      "Select an SSP scenario.";
    return;
  }

  currentEpochLabel = getEpochLabel();

  let response;
  try {
    response = await fetch(
      `/api/pilot/zones/index/${currentIndexCode}${epochPath}`
    );
  } catch (err) {
    clearIndexView("Could not reach the API to load index data.");
    return;
  }

  if (!response.ok) {
    const detail = await response.text();
    let message = `Not delivered yet for ${currentIndexCode} (${currentEpochLabel}).`;
    try {
      message = JSON.parse(detail).detail || message;
    } catch (err) {
      // Keep the default message if the body wasn't JSON.
    }
    clearIndexView(message);
    return;
  }

  currentIndexData = await response.json();

  const entry = indicesCatalog.indices[currentIndexCode];
  renderIndexZones(
    currentIndexData,
    `${currentIndexCode} — ${entry.name} (${currentEpochLabel})`
  );
  renderZonePanel();
}

function populateIndexSelect(crop) {
  const indexSelect = document.getElementById("indice-select");
  indexSelect.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "select an index";
  indexSelect.appendChild(placeholder);

  Object.entries(indicesCatalog.indices)
    .filter(([, entry]) => entry.crops.includes(crop))
    .sort(([codeA], [codeB]) => codeA.localeCompare(codeB))
    .forEach(([code, entry]) => {
      const option = document.createElement("option");
      option.value = code;
      option.textContent = `${code} - ${entry.name}`;
      indexSelect.appendChild(option);
    });

  indexSelect.disabled = false;
}

async function loadIndicesCatalog() {
  try {
    const response = await fetch("/api/indices");
    if (!response.ok) {
      throw new Error(await response.text());
    }
    indicesCatalog = await response.json();
  } catch (err) {
    showBannerWarning(
      "Indices catalog not found. Run 'python -m scripts.build_indices_catalog' " +
      "locally, then restart the API."
    );
    document.getElementById("banner-subtitle").textContent = SELECT_CROP_PROMPT;
    return;
  }

  document.getElementById("cultura-select").disabled = false;
  document.getElementById("banner-subtitle").textContent = SELECT_CROP_PROMPT;
}

function setupFilters() {
  const culturaSelect = document.getElementById("cultura-select");
  culturaSelect.innerHTML = "";
  const cropPlaceholder = document.createElement("option");
  cropPlaceholder.value = "";
  cropPlaceholder.textContent = "select a crop";
  culturaSelect.appendChild(cropPlaceholder);

  CULTURAS.forEach((cultura) => {
    const option = document.createElement("option");
    option.value = cultura.toLowerCase();
    option.textContent = cultura;
    culturaSelect.appendChild(option);
  });

  const periodSelect = document.getElementById("period-select");
  FUTURE_PERIODS.forEach((period) => {
    const option = document.createElement("option");
    option.value = period;
    option.textContent = `Future · ${period}`;
    periodSelect.appendChild(option);
  });
  periodSelect.disabled = false;

  const sspSelect = document.getElementById("ssp-select");

  const populateSsp = () => {
    sspSelect.innerHTML = "";

    if (periodSelect.value === "historical") {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "n/a (historical)";
      sspSelect.appendChild(option);
      sspSelect.disabled = true;
      return;
    }

    FUTURE_SCENARIOS.forEach((scenario) => {
      const option = document.createElement("option");
      option.value = scenario.value;
      option.textContent = scenario.label;
      sspSelect.appendChild(option);
    });
    sspSelect.disabled = false;
  };

  populateSsp();

  culturaSelect.addEventListener("change", () => {
    const indexSelect = document.getElementById("indice-select");

    if (!culturaSelect.value) {
      indexSelect.innerHTML = '<option value="">select a crop</option>';
      indexSelect.disabled = true;
      updateIndexView();
      return;
    }

    populateIndexSelect(culturaSelect.value);
    updateIndexView();
  });

  document
    .getElementById("indice-select")
    .addEventListener("change", updateIndexView);

  periodSelect.addEventListener("change", () => {
    populateSsp();
    updateIndexView();
  });
  sspSelect.addEventListener("change", updateIndexView);
}

async function init() {
  initMap();
  setupFilters();
  await loadZones();
  await loadIndicesCatalog();
}

init();
