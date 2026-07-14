/* İslam Atlası v2 — varlık sayfası (H11 S8).
   Projeksiyon dokümanını Typesense'ten id-filtresiyle çeker (search-only
   anahtar documents/<id> GET'e yetmez; filter_by id ile arama yeterli). */
(function () {
  const TS = window.IAC_CONFIG;
  const TYPE_TR = { person: "Kişi", place: "Yer", work: "Eser", institution: "Yapı", dynasty: "Hanedan", event: "Olay" };
  const LAYER_TR = {
    "yaqut": "Yâkût Mu'cem", "le-strange": "Le Strange", "makdisi": "Makdisî",
    "bosworth": "Bosworth", "evliya-celebi": "Evliyâ Çelebi", "ibn-battuta": "İbn Battûta",
    "darp-islam": "Darp İslam (sikke)", "konya-city-atlas": "Konya City Atlas",
    "maqrizi-khitat": "Makrîzî Hıtat", "science-layer": "Bilim Katmanı", "openiti": "OpenITI",
    "dia": "TDV İslâm Ansiklopedisi", "el-alam": "el-Aʿlâm", "scholars": "Âlim Kartları (v1)",
    "ei1": "İslâm Ansiklopedisi (EI1)", "manual": "Editöryal",
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
  const $root = document.getElementById("entity");
  const id = new URLSearchParams(location.search).get("id");

  function esc(s) { return (s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  async function fetchDoc(docId) {
    const params = new URLSearchParams({
      q: "*", query_by: "prefLabel_tr", per_page: 1,
      // id filtresi TIRNAKSIZ ister — çift-tırnaklı form 0 sonuç döndürüyor
      // (Typesense 29.0'a karşı doğrulandı, H11 S8).
      filter_by: `id:=${docId}`,
    });
    const r = await fetch(`${TS.url}/collections/iac_entities/documents/search?${params}`, {
      headers: { "X-TYPESENSE-API-KEY": TS.searchKey },
    });
    const d = await r.json();
    return d.hits && d.hits.length ? d.hits[0].document : null;
  }

  function factRows(d) {
    const rows = [];
    if (d.start_year_ce != null) rows.push(["Başlangıç (m.)", d.start_year_ce]);
    if (d.end_year_ce != null && d.end_year_ce !== d.start_year_ce) rows.push(["Bitiş (m.)", d.end_year_ce]);
    if (d.century_ah != null) rows.push(["Hicrî yüzyıl", d.century_ah + "."]);
    if (d.subtypes && d.subtypes.length) rows.push(["Alt tür", d.subtypes.map((s) => SUBTYPE_TR[s] || s).join(", ")]);
    if (d.language && d.language.length) rows.push(["Diller", d.language.join(", ")]);
    rows.push(["Kalıcı kimlik", d.id]);
    return rows;
  }

  async function main() {
    if (!id) { $root.innerHTML = '<p class="loading">Varlık kimliği eksik.</p>'; return; }
    const d = await fetchDoc(id);
    if (!d) { $root.innerHTML = '<p class="loading">Kayıt bulunamadı: ' + esc(id) + "</p>"; return; }
    document.title = "İslam Atlası — " + (d.prefLabel_tr || d.prefLabel_en || d.id);

    const relLinks = (d.related_pids || []).map((pid, i) => {
      const label = (d.related_labels || [])[i] || pid;
      return `<li><a href="entity.html?id=${encodeURIComponent(pid)}">${esc(label)}</a>
              <span class="facet-count">${esc(pid.split(":")[1].split("-")[0])}</span></li>`;
    }).join("");

    const layers = (d.source_layer || []).map((l) =>
      `<span class="meta-chip">${esc(LAYER_TR[l] || l)}</span>`).join(" ");

    $root.innerHTML = `
      <div class="entity-header">
        <span class="type-chip type-${d.entity_type}">${TYPE_TR[d.entity_type] || d.entity_type}</span>
        <h1>${esc(d.prefLabel_tr || d.prefLabel_en || d.id)}</h1>
        ${d.prefLabel_ar ? `<span class="entity-ar">${esc(d.prefLabel_ar)}</span>` : ""}
      </div>
      ${d.prefLabel_en && d.prefLabel_en !== d.prefLabel_tr ? `<p class="entity-en">${esc(d.prefLabel_en)}${d.prefLabel_translit && d.prefLabel_translit !== d.prefLabel_en ? " · " + esc(d.prefLabel_translit) : ""}</p>` : ""}
      <div class="hit-meta">${layers}</div>
      <div class="entity-grid">
        <div class="entity-main">
          ${d.description_tr ? `<p class="desc">${esc(d.description_tr)}</p>` : ""}
          ${d.description_en ? `<p class="desc" style="color:var(--ink-soft)">${esc(d.description_en)}</p>` : ""}
          ${d.description_ar ? `<p class="desc desc-ar">${esc(d.description_ar)}</p>` : ""}
          ${(d.altLabels || []).length ? `<div class="panel"><h2>Diğer adlar</h2>${d.altLabels.map((a) => `<span class="meta-chip">${esc(a)}</span>`).join(" ")}</div>` : ""}
        </div>
        <aside>
          <div class="panel"><h2>Künye</h2>${factRows(d).map(([k, v]) =>
            `<div class="fact-row"><span class="fact-key">${k}</span><span class="fact-val">${esc(String(v))}</span></div>`).join("")}
          </div>
          ${d._geo ? `<div class="panel"><h2>Harita</h2><div id="map"></div></div>` : ""}
          ${relLinks ? `<div class="panel"><h2>İlişkili varlıklar</h2><ul class="rel-list">${relLinks}</ul></div>` : ""}
        </aside>
      </div>`;

    if (d._geo && window.L) {
      const map = L.map("map", { scrollWheelZoom: false }).setView(d._geo, 12);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap",
      }).addTo(map);
      L.marker(d._geo).addTo(map);
    }
  }
  main();
})();
