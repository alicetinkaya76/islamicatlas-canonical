/* İslam Atlası v2 — arama sayfası (H11 S8).
   Doğrudan Typesense REST'e konuşur (search-only anahtar, config.js). */
(function () {
  const TS = window.IAC_CONFIG;
  const QUERY_BY = "prefLabel_tr,prefLabel_en,prefLabel_ar,prefLabel_translit,altLabels,description_tr,description_en";
  const PER_PAGE = 12;

  const TYPE_TR = {
    person: "Kişi", place: "Yer", work: "Eser",
    institution: "Yapı", dynasty: "Hanedan", event: "Olay",
  };
  const LAYER_TR = {
    "yaqut": "Yâkût Mu'cem", "le-strange": "Le Strange", "makdisi": "Makdisî",
    "bosworth": "Bosworth", "evliya-celebi": "Evliyâ Çelebi",
    "ibn-battuta": "İbn Battûta", "darp-islam": "Darp İslam (sikke)",
    "konya-city-atlas": "Konya City Atlas", "maqrizi-khitat": "Makrîzî Hıtat",
    "science-layer": "Bilim Katmanı", "openiti": "OpenITI",
    "dia": "TDV İslâm Ansiklopedisi", "el-alam": "el-Aʿlâm",
    "scholars": "Âlim Kartları (v1)", "ei1": "İslâm Ansiklopedisi (EI1)",
    "manual": "Editöryal",
  };
  const SUBTYPE_TR = {
    // yapı alt-türleri
    mosque: "Cami", madrasa: "Medrese", shrine: "Türbe", hammam: "Hamam",
    caravanserai: "Han", palace: "Saray", bridge: "Köprü", church: "Kilise",
    fountain: "Çeşme", market: "Çarşı", tekke: "Tekke", library: "Kütüphane",
    hospital: "Dârüşşifâ", observatory: "Rasathane", other: "Diğer",
    // kişi alt-türleri (subtypes alanı tüm tiplerde ortak)
    scholar: "Âlim", poet: "Şair", ruler: "Hükümdar", narrator: "Râvi",
    calligrapher: "Hattat", architect: "Mimar", mufti: "Müftü",
    physician: "Tabip", historian: "Tarihçi", philosopher: "Filozof",
    astronomer: "Astronom", mathematician: "Matematikçi", sufi: "Sûfî",
    traveler: "Seyyah", geographer: "Coğrafyacı", vizier: "Vezir",
    judge: "Kadı", commander: "Kumandan",
    // olay alt-türleri
    battle: "Savaş", founding: "Kuruluş", composition: "Telif",
    disaster: "Felaket",
  };

  const state = { q: "", page: 1, filters: {} }; // filters: {facetField: value}

  const $q = document.getElementById("q");
  const $hits = document.getElementById("hits");
  const $meta = document.getElementById("meta");
  const $facets = document.getElementById("facets");
  const $pager = document.getElementById("pager");
  const $hero = document.getElementById("hero");

  function filterBy() {
    const parts = [];
    for (const [f, v] of Object.entries(state.filters)) parts.push(`${f}:=${JSON.stringify(v)}`);
    return parts.join(" && ");
  }

  async function search() {
    const params = new URLSearchParams({
      q: state.q || "*",
      query_by: QUERY_BY,
      per_page: PER_PAGE,
      page: state.page,
      facet_by: "entity_type,source_layer,subtypes,century_ah",
      max_facet_values: 12,
      highlight_full_fields: "prefLabel_tr,prefLabel_en",
      num_typos: 1,
    });
    const fb = filterBy();
    if (fb) params.set("filter_by", fb);
    const r = await fetch(`${TS.url}/collections/iac_entities/documents/search?${params}`, {
      headers: { "X-TYPESENSE-API-KEY": TS.searchKey },
    });
    if (!r.ok) {
      $meta.textContent = "Arama servisine ulaşılamadı (" + r.status + ").";
      return;
    }
    render(await r.json());
  }

  function esc(s) { return (s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  function highlightOf(hit, field) {
    const h = (hit.highlights || []).find((x) => x.field === field);
    return h ? h.snippet || h.value : null;
  }

  function render(res) {
    $hero.classList.toggle("compact", !!state.q || Object.keys(state.filters).length > 0);
    const found = res.found ?? 0;
    $meta.textContent = `${found.toLocaleString("tr-TR")} sonuç · ${res.search_time_ms} ms`;

    $hits.innerHTML = (res.hits || []).map((hit) => {
      const d = hit.document;
      const title = highlightOf(hit, "prefLabel_tr") || esc(d.prefLabel_tr || d.prefLabel_en || d.id);
      const years = [d.start_year_ce, d.end_year_ce].filter((x) => x != null);
      const yearsTxt = years.length ? `${years[0]}${years.length > 1 && years[1] !== years[0] ? "–" + years[1] : ""} m.` : "";
      const layers = (d.source_layer || []).map((l) => LAYER_TR[l] || l);
      const subs = (d.subtypes || []).map((s) => SUBTYPE_TR[s] || s);
      const descRaw = d.description_tr || d.description_en || "";
      const desc = descRaw ? esc(descRaw.slice(0, 220)) + (descRaw.length > 220 ? "…" : "") : "";
      return `<article class="hit">
        <div class="hit-top">
          <span class="type-chip type-${d.entity_type}">${TYPE_TR[d.entity_type] || d.entity_type}</span>
          <a class="hit-title" href="entity.html?id=${encodeURIComponent(d.id)}">${title}</a>
          ${d.prefLabel_ar ? `<span class="hit-ar">${esc(d.prefLabel_ar)}</span>` : ""}
        </div>
        ${desc ? `<p class="hit-snippet">${desc}</p>` : ""}
        <div class="hit-meta">
          ${yearsTxt ? `<span class="meta-chip">${yearsTxt}</span>` : ""}
          ${subs.map((s) => `<span class="meta-chip">${esc(s)}</span>`).join("")}
          ${layers.map((l) => `<span class="meta-chip">${esc(l)}</span>`).join("")}
          ${d.has_coords ? `<span class="meta-chip">📍 haritada</span>` : ""}
        </div>
      </article>`;
    }).join("") || `<p class="loading">Sonuç yok.</p>`;

    renderFacets(res.facet_counts || []);
    renderPager(found);
    if (mapMode) renderMap();
  }

  const FACET_TITLES = { entity_type: "Tür", source_layer: "Kaynak katmanı", subtypes: "Alt tür", century_ah: "Hicrî yüzyıl" };
  const FACET_LABEL = {
    entity_type: (v) => TYPE_TR[v] || v,
    source_layer: (v) => LAYER_TR[v] || v,
    subtypes: (v) => SUBTYPE_TR[v] || v,
    century_ah: (v) => v + ". yüzyıl",
  };

  function renderFacets(fc) {
    $facets.innerHTML = fc.map((f) => {
      if (!f.counts.length) return "";
      const rows = f.counts.map((c) => {
        const active = state.filters[f.field_name] === c.value;
        return `<div class="facet-item ${active ? "active" : ""}" data-f="${f.field_name}" data-v="${esc(c.value)}">
          <span>${esc(FACET_LABEL[f.field_name](c.value))}</span>
          <span class="facet-count">${c.count.toLocaleString("tr-TR")}</span>
        </div>`;
      }).join("");
      return `<div class="facet-group"><h3>${FACET_TITLES[f.field_name] || f.field_name}</h3>${rows}</div>`;
    }).join("");
    $facets.querySelectorAll(".facet-item").forEach((el) => {
      el.addEventListener("click", () => {
        const f = el.dataset.f, v = el.dataset.v;
        if (state.filters[f] === v) delete state.filters[f];
        else state.filters[f] = v;
        state.page = 1;
        search();
      });
    });
  }

  function renderPager(found) {
    $pager.hidden = mapMode;   // harita modunda liste sayfalayıcısı gizli kalır
    const pages = Math.ceil(found / PER_PAGE);
    if (pages <= 1) { $pager.innerHTML = ""; return; }
    $pager.innerHTML = `
      <button id="prev" ${state.page <= 1 ? "disabled" : ""}>← Önceki</button>
      <button disabled>${state.page} / ${Math.min(pages, 250)}</button>
      <button id="next" ${state.page >= pages ? "disabled" : ""}>Sonraki →</button>`;
    const prev = document.getElementById("prev"), next = document.getElementById("next");
    if (prev) prev.onclick = () => { state.page--; search(); window.scrollTo(0, 0); };
    if (next) next.onclick = () => { state.page++; search(); window.scrollTo(0, 0); };
  }

  // ---------- harita görünümü (H11 S9) ----------
  const $hitsEl = document.getElementById("hits");
  const $mapEl = document.getElementById("results-map");
  const $btnList = document.getElementById("view-list");
  const $btnMap = document.getElementById("view-map");
  let mapMode = false, map = null, markers = null;

  function setMode(m) {
    mapMode = m;
    $btnList.classList.toggle("active", !m);
    $btnMap.classList.toggle("active", m);
    $hitsEl.hidden = m; $pager.hidden = m; $mapEl.hidden = !m;
    if (m) renderMap();
  }
  $btnList.addEventListener("click", () => setMode(false));
  $btnMap.addEventListener("click", () => setMode(true));

  async function renderMap() {
    if (!window.L) return;
    if (!map) {
      map = L.map("results-map", { scrollWheelZoom: true }).setView([35, 38], 4);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        { attribution: "© OpenStreetMap" }).addTo(map);
      markers = L.layerGroup().addTo(map);
    }
    setTimeout(() => map.invalidateSize(), 60);
    // Aynı sorgu+filtre, coords şartıyla, ilk 250 geo-hit
    const params = new URLSearchParams({
      q: state.q || "*", query_by: QUERY_BY, per_page: 250, page: 1,
      include_fields: "id,entity_type,prefLabel_tr,prefLabel_en,_geo,subtypes",
    });
    const fb = [filterBy(), "has_coords:true"].filter(Boolean).join(" && ");
    params.set("filter_by", fb);
    const r = await fetch(`${TS.url}/collections/iac_entities/documents/search?${params}`, {
      headers: { "X-TYPESENSE-API-KEY": TS.searchKey },
    });
    if (!r.ok) return;
    const res = await r.json();
    markers.clearLayers();
    const pts = [];
    for (const h of res.hits || []) {
      const d = h.document;
      if (!d._geo) continue;
      pts.push(d._geo);
      const name = d.prefLabel_tr || d.prefLabel_en || d.id;
      L.circleMarker(d._geo, {
        radius: 6, weight: 1.5, color: "#5f3d1c",
        fillColor: { person: "#7a4d9e", place: "#1f6f6b", work: "#a3612d",
                     institution: "#b0453a", dynasty: "#34627d", event: "#6d7332" }[d.entity_type] || "#8a5a2b",
        fillOpacity: .85,
      }).bindPopup(`<div class="map-popup"><a href="entity.html?id=${encodeURIComponent(d.id)}">${esc(name)}</a><br>${TYPE_TR[d.entity_type] || d.entity_type}${(d.subtypes || []).length ? " · " + d.subtypes.map((s) => SUBTYPE_TR[s] || s).join(", ") : ""}</div>`)
        .addTo(markers);
    }
    const note = res.found > 250 ? ` (ilk 250 nokta gösteriliyor / ${res.found.toLocaleString("tr-TR")})` : "";
    $meta.textContent = `${res.found.toLocaleString("tr-TR")} koordinatlı sonuç${note}`;
    if (pts.length) map.fitBounds(L.latLngBounds(pts).pad(0.2), { maxZoom: 9 });
  }

  let t = null;
  $q.addEventListener("input", () => {
    clearTimeout(t);
    t = setTimeout(() => { state.q = $q.value.trim(); state.page = 1; search(); }, 180);
  });

  const initQ = new URLSearchParams(location.search).get("q");
  if (initQ) { $q.value = initQ; state.q = initQ; }
  search();
})();
