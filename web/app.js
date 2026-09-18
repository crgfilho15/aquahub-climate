const MONTH_LABELS = [
  "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
  "Jul", "Ago", "Set", "Out", "Nov", "Dez",
];

const MONTH_NAMES_FULL = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

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

function drawMonthlyChart(svg, monthlyValues) {
  svg.innerHTML = "";

  const width = 360;
  const height = 180;
  const padding = { top: 12, right: 12, bottom: 24, left: 32 };

  const min = Math.min(...monthlyValues);
  const max = Math.max(...monthlyValues);
  const span = max - min || 1;

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const xFor = (i) =>
    padding.left + (i / (monthlyValues.length - 1)) * plotWidth;

  const yFor = (v) =>
    padding.top + plotHeight - ((v - min) / span) * plotHeight;

  const points = monthlyValues
    .map((v, i) => `${xFor(i)},${yFor(v)}`)
    .join(" ");

  const ns = "http://www.w3.org/2000/svg";

  const axis = document.createElementNS(ns, "line");
  axis.setAttribute("x1", padding.left);
  axis.setAttribute("y1", height - padding.bottom);
  axis.setAttribute("x2", width - padding.right);
  axis.setAttribute("y2", height - padding.bottom);
  axis.setAttribute("stroke", "#c7ccd3");
  svg.appendChild(axis);

  const polyline = document.createElementNS(ns, "polyline");
  polyline.setAttribute("points", points);
  polyline.setAttribute("fill", "none");
  polyline.setAttribute("stroke", "#2f6fb2");
  polyline.setAttribute("stroke-width", "2");
  svg.appendChild(polyline);

  monthlyValues.forEach((v, i) => {
    const circle = document.createElementNS(ns, "circle");
    circle.setAttribute("cx", xFor(i));
    circle.setAttribute("cy", yFor(v));
    circle.setAttribute("r", "2.5");
    circle.setAttribute("fill", "#2f6fb2");
    svg.appendChild(circle);

    if (i % 2 === 0) {
      const label = document.createElementNS(ns, "text");
      label.setAttribute("x", xFor(i));
      label.setAttribute("y", height - padding.bottom + 14);
      label.setAttribute("font-size", "9");
      label.setAttribute("fill", "#5b6675");
      label.setAttribute("text-anchor", "middle");
      label.textContent = MONTH_LABELS[i];
      svg.appendChild(label);
    }
  });

  // Crosshair + snapped point, hidden until hover/focus.
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

  // Tooltip: value leads (bold, high-contrast), month label secondary.
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

  // The whole plot area is the hit target, per interaction rules: the
  // crosshair finds the nearest month, the pointer never has to land
  // exactly on a point.
  const hitArea = document.createElementNS(ns, "rect");
  hitArea.setAttribute("x", padding.left);
  hitArea.setAttribute("y", padding.top);
  hitArea.setAttribute("width", plotWidth);
  hitArea.setAttribute("height", plotHeight);
  hitArea.setAttribute("fill", "transparent");
  svg.appendChild(hitArea);

  const updateAt = (monthIndex) => {
    const clamped = Math.max(
      0,
      Math.min(monthlyValues.length - 1, monthIndex)
    );
    const px = xFor(clamped);
    const py = yFor(monthlyValues[clamped]);

    crosshair.setAttribute("x1", px);
    crosshair.setAttribute("x2", px);
    crosshair.setAttribute("visibility", "visible");

    highlight.setAttribute("cx", px);
    highlight.setAttribute("cy", py);
    highlight.setAttribute("visibility", "visible");

    const valueText = `${monthlyValues[clamped].toFixed(2)} °C`;
    const labelText = MONTH_NAMES_FULL[clamped];

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

    // Keep the tooltip inside the chart, flipping below the point
    // when there is not enough room above it.
    let tooltipY = py - boxHeight - 6;
    if (tooltipY < 0) {
      tooltipY = py + 10;
    }

    let tooltipX = px;
    tooltipX = Math.max(boxWidth / 2, Math.min(width - boxWidth / 2, tooltipX));

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

  const nearestMonthForClientX = (clientX) => {
    const rect = svg.getBoundingClientRect();
    const svgX = ((clientX - rect.left) / rect.width) * width;
    const relative = (svgX - padding.left) / plotWidth;
    return Math.round(relative * (monthlyValues.length - 1));
  };

  hitArea.addEventListener("pointermove", (event) => {
    updateAt(nearestMonthForClientX(event.clientX));
  });
  hitArea.addEventListener("pointerleave", hide);

  // Keyboard access: arrow keys step through months, matching the
  // hover experience for non-pointer users.
  svg.setAttribute("tabindex", "0");
  svg.setAttribute("role", "img");
  svg.setAttribute(
    "aria-label",
    "Climatologia mensal de temperatura, use as setas para navegar pelos meses"
  );

  let focusedMonth = 0;
  svg.addEventListener("focus", () => updateAt(focusedMonth));
  svg.addEventListener("blur", hide);
  svg.addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight") {
      focusedMonth = Math.min(monthlyValues.length - 1, focusedMonth + 1);
      updateAt(focusedMonth);
      event.preventDefault();
    } else if (event.key === "ArrowLeft") {
      focusedMonth = Math.max(0, focusedMonth - 1);
      updateAt(focusedMonth);
      event.preventDefault();
    }
  });
}

// Gaussian kernel density estimate over a small set of observed
// values (e.g. one value per municipality/GCM within a zone) - turns
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
// observed values, with the same interaction conventions as
// drawMonthlyChart (crosshair, value-leads tooltip, keyboard nav) and
// a rug plot along the axis showing each real observed value under
// the smoothed curve. What "values" contains (one per municipality
// within a zone? one per GCM? something else?) is not yet confirmed
// with the professor - this function only draws whatever array it is
// given.
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
    const labelText = "densidade estimada";

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
    "Distribuição de valores do índice selecionado na zona, use as " +
    "setas para navegar"
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

function showPanel(properties) {
  document.getElementById("panel-empty").hidden = true;
  const content = document.getElementById("panel-content");
  content.hidden = false;

  document.getElementById("panel-name").textContent = properties.municipio;

  document.getElementById("panel-annual").textContent =
    `Temperatura média anual (${properties.period}): ` +
    `${properties.annual_mean_celsius.toFixed(2)} °C`;

  const anomalyEl = document.getElementById("panel-anomaly");
  if (properties.scenario) {
    const delta = properties.annual_anomaly_absolute;
    const sign = delta >= 0 ? "+" : "";
    anomalyEl.textContent =
      `Cenário ${properties.scenario} · vs. histórico (1981-2010): ` +
      `${sign}${delta.toFixed(2)} °C`;
    anomalyEl.hidden = false;
  } else {
    anomalyEl.hidden = true;
  }

  document.getElementById("panel-source").textContent = properties.scenario
    ? `Ensemble de ${properties.n_gcms || "vários"} modelos · ` +
      `variável: ${properties.variable}`
    : `Fonte: ${properties.source} · variável: ${properties.variable}`;

  drawMonthlyChart(
    document.getElementById("panel-chart"),
    properties.monthly_mean_celsius
  );
}

function buildLegend(min, max) {
  const legend = L.control({ position: "bottomright" });

  legend.onAdd = () => {
    const div = L.DomUtil.create("div", "info-legend");
    const steps = 5;

    let html = '<div id="legend"><strong>Temp. média anual (°C)</strong><br>';

    for (let i = 0; i < steps; i += 1) {
      const value = min + ((max - min) * i) / (steps - 1);
      const color = temperatureToColor(value, min, max);
      html += `<span class="swatch" style="background:${color}"></span>${value.toFixed(1)}<br>`;
    }

    html += "</div>";
    div.innerHTML = html;

    return div;
  };

  return legend;
}

let map = null;
let currentGeoLayer = null;
let currentLegend = null;

function initMap() {
  map = L.map("map");

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "© OpenStreetMap contributors",
  }).addTo(map);
}

function resetPanel() {
  document.getElementById("panel-content").hidden = true;
  document.getElementById("panel-empty").hidden = false;
}

function renderFeatureCollection(featureCollection) {
  if (currentGeoLayer) {
    map.removeLayer(currentGeoLayer);
  }
  if (currentLegend) {
    map.removeControl(currentLegend);
  }

  const values = featureCollection.features.map(
    (f) => f.properties.annual_mean_celsius
  );
  const min = Math.min(...values);
  const max = Math.max(...values);

  currentGeoLayer = L.geoJSON(featureCollection, {
    style: (feature) => ({
      fillColor: temperatureToColor(
        feature.properties.annual_mean_celsius,
        min,
        max
      ),
      fillOpacity: 0.75,
      weight: 1,
      color: "#3a4250",
    }),
    onEachFeature: (feature, layer) => {
      layer.bindTooltip(
        `${feature.properties.municipio}: ` +
        `${feature.properties.annual_mean_celsius.toFixed(2)} °C`
      );
      layer.on("click", () => showPanel(feature.properties));
    },
  }).addTo(map);

  map.fitBounds(currentGeoLayer.getBounds(), { padding: [16, 16] });

  currentLegend = buildLegend(min, max);
  currentLegend.addTo(map);
}

// Future GeoJSON properties are named differently
// (annual_ensemble_mean/monthly_ensemble_mean) from the historical
// ones (annual_mean_celsius/monthly_mean_celsius) that
// renderFeatureCollection/showPanel already know how to draw. Rather
// than teaching every render function two naming schemes, normalize
// once here so the rest of the rendering path stays unchanged.
function normalizeFutureFeatureCollection(featureCollection) {
  return {
    type: "FeatureCollection",
    features: featureCollection.features.map((feature) => ({
      ...feature,
      properties: {
        ...feature.properties,
        annual_mean_celsius: feature.properties.annual_ensemble_mean,
        monthly_mean_celsius: feature.properties.monthly_ensemble_mean,
      },
    })),
  };
}

async function loadFuturePeriodOptions(slug) {
  const periodSelect = document.getElementById("period-select");
  periodSelect.innerHTML =
    '<option value="historical">Histórico (1981-2010)</option>';

  let slices = [];
  try {
    const response = await fetch(`/api/pilot/${slug}/future`);
    slices = await response.json();
  } catch (err) {
    slices = [];
  }

  for (const slice of slices) {
    const option = document.createElement("option");
    option.value = `${slice.variable}|${slice.scenario}|${slice.period}`;
    const scenarioLabel = slice.scenario.toUpperCase();
    option.textContent =
      `Futuro · ${scenarioLabel} · ${slice.period} (${slice.variable})`;
    periodSelect.appendChild(option);
  }

  periodSelect.disabled = false;
  periodSelect.value = "historical";
}

async function loadPeriodData(slug, selection) {
  const subtitle = document.getElementById("banner-subtitle");
  resetPanel();

  if (selection === "historical") {
    await loadHistoricalRegion(slug);
    return;
  }

  const [variable, scenario, period] = selection.split("|");

  let meta;
  try {
    const metaResponse = await fetch(
      `/api/pilot/${slug}/future/${variable}/${scenario}/${period}/meta`
    );
    if (!metaResponse.ok) {
      throw new Error(await metaResponse.text());
    }
    meta = await metaResponse.json();
  } catch (err) {
    subtitle.innerHTML =
      "Dados futuros não encontrados. Rode " +
      "<code>python -m scripts.build_future_pilot_data " +
      "&lt;ensemble.csv&gt;</code> localmente e reinicie a API.";
    return;
  }

  subtitle.innerHTML =
    `${meta.region_name} · ${meta.dataset} · ` +
    `variável <strong>${meta.variable}</strong> · ` +
    `cenário <strong>${meta.scenario}</strong> · ` +
    `período <strong>${meta.period}</strong> · ` +
    `ensemble de <strong>${meta.gcms.length} GCMs</strong> · ` +
    `metodologia: <strong>${meta.methodology_status}</strong>`;

  const geoResponse = await fetch(
    `/api/pilot/${slug}/future/${variable}/${scenario}/${period}`
  );
  const featureCollection = await geoResponse.json();

  renderFeatureCollection(
    normalizeFutureFeatureCollection(featureCollection)
  );
}

async function loadHistoricalRegion(slug) {
  const subtitle = document.getElementById("banner-subtitle");
  const warning = document.getElementById("banner-warning");
  warning.hidden = true;

  let meta;
  try {
    const metaResponse = await fetch(`/api/pilot/${slug}/meta`);
    if (!metaResponse.ok) {
      throw new Error(await metaResponse.text());
    }
    meta = await metaResponse.json();
  } catch (err) {
    subtitle.innerHTML =
      "Dados do piloto não encontrados. Rode " +
      `<code>python -m scripts.build_pilot_region --region ${slug}</code> ` +
      "localmente e reinicie a API.";
    return;
  }

  subtitle.innerHTML =
    `${meta.region_name} · ${meta.dataset} · ` +
    `variável <strong>${meta.variable}</strong> · ` +
    `período <strong>${meta.period}</strong> · ` +
    `metodologia: <strong>${meta.methodology_status}</strong>`;

  if (!meta.future_scenarios_included) {
    warning.textContent =
      "Cenários futuros (SSP/GCM) ainda não incluídos — " +
      "aguardando validação metodológica com o professor.";
    warning.hidden = false;
  }

  const geoResponse = await fetch(`/api/pilot/${slug}`);
  const featureCollection = await geoResponse.json();

  renderFeatureCollection(featureCollection);
}

async function loadRegion(slug) {
  resetPanel();

  const periodSelect = document.getElementById("period-select");
  periodSelect.value = "historical";

  await loadHistoricalRegion(slug);
  await loadFuturePeriodOptions(slug);
}

async function init() {
  initMap();

  const select = document.getElementById("region-select");
  const subtitle = document.getElementById("banner-subtitle");

  let regions = [];
  try {
    const response = await fetch("/api/pilot");
    regions = await response.json();
  } catch (err) {
    regions = [];
  }

  if (regions.length === 0) {
    subtitle.innerHTML =
      "Nenhum piloto construído ainda. Rode " +
      "<code>python -m scripts.build_pilot_region</code> localmente " +
      "e reinicie a API.";
    select.innerHTML = '<option value="">nenhuma região disponível</option>';
    return;
  }

  select.innerHTML = "";
  for (const region of regions) {
    const option = document.createElement("option");
    option.value = region.slug;
    option.textContent = region.label;
    select.appendChild(option);
  }
  select.disabled = false;

  select.addEventListener("change", () => loadRegion(select.value));

  const periodSelect = document.getElementById("period-select");
  periodSelect.addEventListener("change", () => {
    loadPeriodData(select.value, periodSelect.value);
  });

  await loadRegion(regions[0].slug);
}

init();
