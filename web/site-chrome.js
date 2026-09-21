// Shared header/footer for every page of the site. Each page sets
// document.body.dataset.activePage (e.g. "home", "atlas") so the
// matching nav link gets highlighted, and includes a <div
// id="site-header"></div> / <div id="site-footer"></div> pair for
// this script to fill in. Kept as one small script rather than
// duplicating the nav/footer markup in every .html file, so adding a
// page later only means editing NAV_ITEMS once.

const BRAND_MARK = `
  <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
    <circle cx="14" cy="14" r="13" stroke="#2f6fb2" stroke-width="2" />
    <path d="M4 16c2.5-3 5-3 7 0s4.5 3 7 0 5-3 7 0" stroke="#2f6fb2" stroke-width="2" fill="none" stroke-linecap="round" />
    <path d="M9 11l3-4 3 4 3-4" stroke="#9fb6d4" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
`;

const NAV_ITEMS = [
  { key: "home", label: "Home", href: "index.html" },
  { key: "about", label: "About the Project", href: "about.html" },
  { key: "zones", label: "Intervention Zones", href: "zones.html" },
  { key: "atlas", label: "Climate Atlas", href: "atlas.html" },
  { key: "team", label: "Team", href: "team.html" },
  { key: "contact", label: "Contact", href: "contact.html" },
];

function renderHeader(activePage) {
  const links = NAV_ITEMS.map((item) => {
    const activeClass = item.key === activePage ? " active" : "";
    return `<li><a class="nav-link${activeClass}" href="${item.href}">${item.label}</a></li>`;
  }).join("");

  return `
    <nav class="site-nav">
      <a class="brand" href="index.html">
        ${BRAND_MARK}
        AquaHub Climate
      </a>
      <ul>${links}</ul>
    </nav>
  `;
}

function renderFooter() {
  const quickLinks = NAV_ITEMS.map(
    (item) => `<li><a href="${item.href}">${item.label}</a></li>`
  ).join("");

  return `
    <div class="footer-grid">
      <div>
        <div class="brand">${BRAND_MARK} AquaHub Climate</div>
        <p>
          Climate and agroclimatic atlas for the Douro river basin,
          covering Douro, Beira Interior and Terras de Trás-os-Montes
          in Portugal, and Castilla y León and Extremadura in Spain.
        </p>
      </div>
      <div>
        <h4>Navigation</h4>
        <ul>${quickLinks}</ul>
      </div>
      <div>
        <h4>Project</h4>
        <p>Interreg VI-A POCTEP</p>
        <p>Universidade de Trás-os-Montes e Alto Douro (UTAD)</p>
        <p>Research Fellowship BI/UTAD/46/2026</p>
      </div>
    </div>
    <div class="footer-bottom">
      © ${new Date().getFullYear()} AquaHub Climate — research project in active development.
    </div>
  `;
}

function mountSiteChrome() {
  const activePage = document.body.dataset.activePage || "";

  const header = document.getElementById("site-header");
  const footer = document.getElementById("site-footer");

  if (header) {
    header.innerHTML = renderHeader(activePage);
  }

  if (footer) {
    footer.innerHTML = renderFooter();
  }
}

mountSiteChrome();
