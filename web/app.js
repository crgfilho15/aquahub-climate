const COLOR_STOPS = [
  { t: 0.0, color: [49, 100, 175] },
  { t: 0.5, color: [247, 234, 173] },
  { t: 1.0, color: [178, 40, 33] },
];

function temperatureToColor(value, min, max) {
  if (max === min) {
    return "rgb(150,150,150)";
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

  const rgb = lower.color.map((channel, i) =>
    Math.round(channel + (upper.color[i] - channel) * localT)
  );

  return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
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

  const dataMin = Math.min(...values);
  const dataMax = Math.max(...values);
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
// observed values, with a crosshair, value-leads tooltip, keyboard
// nav, and a rug plot along the axis showing each real observed value
// under the smoothed curve. Today "values" is one annual mean
// temperature per municipality within the clicked zone (historical or
// a future ensemble mean, depending on the Period/SSP filters) -
// this is a provisional choice pending confirmation with the
// professor of what the distribution axis should ultimately show
// (see docs/03).
function drawDistributionChart(svg, values, options = {}) {
  svg.innerHTML = "";

  if (!values || values.length === 0) {
    return;
  }

  const width = 300;
  const height = 160;
  const padding = { top: 10, right: 12, bottom: 24, left: 12 };

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

  // Rug plot: one tick per real observed value, under the smoothed
  // curve, so the underlying data isn't hidden by the smoothing.
  values.forEach((v) => {
    const tick = document.createElementNS(ns, "line");
    const tx = xFor(v);
    tick.setAttribute("x1", tx);
    tick.setAttribute("x2", tx);
    tick.setAttribute("y1", height - padding.bottom);
    tick.setAttribute("y2", height - padding.bottom + 5);
    tick.setAttribute("stroke", "#5b6675");
    tick.setAttribute("stroke-width", "1");
    svg.appendChild(tick);
  });

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

// The 4 crop names are confirmed (docs/04); the bioclimatic index
// values/thresholds per crop are not - the professor is calculating
// them and will deliver them to the project. So the crop list itself
// is shown (real), but the select stays disabled until real index
// data exists (see index.html's banner-warning note).
const CULTURAS = ["Grapevine", "Olive", "Almond", "Cherry"];

// Mirrors config/climate.toml's [future] section (periods/scenarios).
const FUTURE_PERIODS = ["2011-2040", "2041-2070", "2071-2100"];
const FUTURE_SCENARIOS = [
  { value: "ssp126", label: "SSP1-2.6 (moderate)" },
  { value: "ssp585", label: "SSP5-8.5 (severe)" },
];
const PILOT_VARIABLE = "tas";

let map = null;
let zonesLayer = null;
let currentLegend = null;
let zoneFeaturesBySlug = {};
let selectedZoneSlug = null;

function initMap() {
  map = L.map("map");

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "© OpenStreetMap contributors",
  }).addTo(map);
}

function buildZonesLegend(min, max) {
  const legend = L.control({ position: "bottomright" });

  legend.onAdd = () => {
    const div = L.DomUtil.create("div", "info-legend");
    const steps = 5;

    let html =
      '<div id="legend"><strong>Mean annual temp. (°C)</strong><br>';

    for (let i = 0; i < steps; i += 1) {
      const value = min + ((max - min) * i) / (steps - 1);
      const color = temperatureToColor(value, min, max);
      html += `<span class="swatch" style="background:${color}"></span>${value.toFixed(1)}<br>`;
    }

    html +=
      '<span class="swatch" style="background:#c7ccd3"></span>' +
      "pending data</div>";
    div.innerHTML = html;

    return div;
  };

  return legend;
}

function zoneStyle(feature, min, max) {
  if (!feature.properties.built) {
    return {
      fillColor: "#c7ccd3",
      fillOpacity: 0.4,
      weight: 1.5,
      color: "#9aa3af",
      dashArray: "4 3",
    };
  }

  return {
    fillColor: temperatureToColor(
      feature.properties.annual_mean_celsius,
      min,
      max
    ),
    fillOpacity: 0.75,
    weight: 1.5,
    color: "#3a4250",
  };
}

async function loadZones() {
  const subtitle = document.getElementById("banner-subtitle");

  let featureCollection;
  try {
    const response = await fetch("/api/pilot/zones");
    if (!response.ok) {
      throw new Error(await response.text());
    }
    featureCollection = await response.json();
  } catch (err) {
    subtitle.innerHTML =
      "No zone has been built yet. Run " +
      "<code>python -m scripts.build_zone_overview</code> locally " +
      "and restart the API.";
    return;
  }

  if (!featureCollection.features || featureCollection.features.length === 0) {
    subtitle.innerHTML =
      "No zone has been built yet. Run " +
      "<code>python -m scripts.build_zone_overview</code> locally " +
      "and restart the API.";
    return;
  }

  zoneFeaturesBySlug = {};
  featureCollection.features.forEach((feature) => {
    zoneFeaturesBySlug[feature.properties.slug] = feature;
  });

  const builtValues = featureCollection.features
    .filter((feature) => feature.properties.built)
    .map((feature) => feature.properties.annual_mean_celsius);

  const min = builtValues.length ? Math.min(...builtValues) : 0;
  const max = builtValues.length ? Math.max(...builtValues) : 1;

  if (zonesLayer) {
    map.removeLayer(zonesLayer);
  }
  if (currentLegend) {
    map.removeControl(currentLegend);
  }

  zonesLayer = L.geoJSON(featureCollection, {
    style: (feature) => zoneStyle(feature, min, max),
    onEachFeature: (feature, layer) => {
      const label = feature.properties.built
        ? `${feature.properties.label}: ` +
          `${feature.properties.annual_mean_celsius.toFixed(2)} °C`
        : `${feature.properties.label} (pending data)`;
      layer.bindTooltip(label);
      layer.on("click", () => selectZone(feature.properties.slug));
    },
  }).addTo(map);

  map.fitBounds(zonesLayer.getBounds(), { padding: [16, 16] });

  if (builtValues.length) {
    currentLegend = buildZonesLegend(min, max);
    currentLegend.addTo(map);
  }

  subtitle.textContent =
    "Click a zone on the map to see its value distribution.";
}

function showDistribution(values, unit, caption) {
  document.getElementById("panel-distribution-caption").textContent =
    caption;
  document.getElementById("panel-distribution-wrapper").hidden = false;
  drawDistributionChart(
    document.getElementById("panel-distribution-chart"),
    values,
    { unit: ` ${unit}` }
  );
}

async function selectZone(slug) {
  selectedZoneSlug = slug;
  const feature = zoneFeaturesBySlug[slug];
  if (!feature) {
    return;
  }

  document.getElementById("panel-empty").hidden = true;
  document.getElementById("panel-content").hidden = false;
  document.getElementById("panel-name").textContent =
    feature.properties.label;

  const annualEl = document.getElementById("panel-annual");
  const pendingEl = document.getElementById("panel-pending");
  const distWrapper = document.getElementById("panel-distribution-wrapper");

  if (!feature.properties.built) {
    annualEl.textContent = "";
    pendingEl.hidden = false;
    distWrapper.hidden = true;
    return;
  }

  pendingEl.hidden = true;

  const period = document.getElementById("period-select").value;

  if (period === "historical") {
    annualEl.textContent =
      "Mean annual temperature (historical 1981-2010): " +
      `${feature.properties.annual_mean_celsius.toFixed(2)} °C`;

    const values = feature.properties.municipality_values.map(
      (m) => m.annual_mean_celsius
    );
    showDistribution(
      values,
      "°C",
      "Distribution of mean annual temperature by municipality in " +
      "the zone (provisional — pending confirmation with the professor)"
    );
    return;
  }

  const scenario = document.getElementById("ssp-select").value;

  if (!scenario) {
    annualEl.textContent = "Select an SSP scenario.";
    distWrapper.hidden = true;
    return;
  }

  annualEl.textContent = "loading future data...";
  distWrapper.hidden = true;

  try {
    const response = await fetch(
      `/api/pilot/${slug}/future/${PILOT_VARIABLE}/${scenario}/${period}`
    );
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const futureFeatureCollection = await response.json();
    const values = futureFeatureCollection.features.map(
      (f) => f.properties.annual_ensemble_mean
    );

    if (values.length === 0) {
      throw new Error("empty future feature collection");
    }

    const mean = values.reduce((a, b) => a + b, 0) / values.length;

    annualEl.textContent =
      `Mean annual temperature (${scenario.toUpperCase()} · ${period}): ` +
      `${mean.toFixed(2)} °C`;

    showDistribution(
      values,
      "°C",
      "Distribution of mean annual temperature (ensemble) by " +
      "municipality in the zone (provisional — pending confirmation " +
      "with the professor)"
    );
  } catch (err) {
    annualEl.textContent =
      "No future data found for this zone. Run " +
      "python -m scripts.build_future_pilot_data locally and " +
      "restart the API.";
    distWrapper.hidden = true;
  }
}

function setupFilters() {
  const culturaSelect = document.getElementById("cultura-select");
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

  const refreshSelectedZone = () => {
    if (selectedZoneSlug) {
      selectZone(selectedZoneSlug);
    }
  };

  periodSelect.addEventListener("change", () => {
    populateSsp();
    refreshSelectedZone();
  });
  sspSelect.addEventListener("change", refreshSelectedZone);
}

async function init() {
  initMap();
  setupFilters();
  await loadZones();
}

init();
