import { useState, useCallback, useRef } from 'react';
import { hn } from '../../data/i18n-utils';
import T from '../../data/i18n';
/* H17 Dalga-0: palet + sanal liste bookkit'ten (görsel çıktı birebir aynı). */
import { GEO_COLORS, GEO_ICONS, GEO_EN, GEO_TR, PERIOD_LABEL, VirtualList } from '../shared/bookkit';

const ITEM_HEIGHT = 68;

/* Yâkût satır çizimi — bookkit VirtualList'e renderItem olarak verilir. */
function renderYaqutRow(e, selectedId, onSelect, lang) {
  return (
    <div key={e.id}
      className={`yaqut-list-item${e.id === selectedId ? ' selected' : ''}`}
      style={{ height: ITEM_HEIGHT }}
      onClick={() => onSelect(e.id)}>
      <div className="yaqut-list-top">
        <span className="yaqut-list-icon" style={{ color: GEO_COLORS[e.gt] || '#90a4ae' }}>
          {GEO_ICONS[e.gt] || '📍'}
        </span>
        <div className="yaqut-list-heading" dir="rtl">{e.h}</div>
      </div>
      <div className="yaqut-list-name">{hn(e, lang)}</div>
      <div className="yaqut-list-meta">
        <span className="yaqut-list-type">{lang === 'tr' ? e.gtt : e.gte}</span>
        {e.ct && <span className="yaqut-list-country"> · {e.ct}</span>}
        {(e.pc > 0) && <span className="yaqut-list-xref"> · 👤{e.pc}</span>}
        {e.ds && <span className="yaqut-list-dia"> · DİA</span>}
      </div>
    </div>
  );
}

export default function YaqutSidebar({
  lang, ty, filtered, search, setSearch,
  selectedGeoTypes, setSelectedGeoTypes,
  selectedCountry, setSelectedCountry,
  selectedLetter, setSelectedLetter,
  selectedPeriod, setSelectedPeriod,
  selectedTags, setSelectedTags,
  crossRefRange, setCrossRefRange,
  selectedId, onSelect,
  topGeoTypes, allCountries, allLetters, topTags, periods,
}) {
  const t = T[lang];
  const [filtersOpen, setFiltersOpen] = useState(true);
  const debounceRef = useRef(null);

  const handleSearchChange = useCallback((e) => {
    const val = e.target.value;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setSearch(val), 200);
  }, [setSearch]);

  const toggleGeoType = useCallback((gt) => {
    setSelectedGeoTypes(prev => {
      const next = new Set(prev);
      if (next.has(gt)) next.delete(gt);
      else next.add(gt);
      return next;
    });
  }, [setSelectedGeoTypes]);

  const toggleTag = useCallback((tag) => {
    setSelectedTags(prev => {
      const next = new Set(prev);
      if (next.has(tag)) next.delete(tag);
      else next.add(tag);
      return next;
    });
  }, [setSelectedTags]);

  return (
    <div className="yaqut-sidebar-inner">
      {/* Search */}
      <div className="yaqut-search-row">
        <span className="yaqut-search-icon">🔍</span>
        <input type="text" className="yaqut-search-input"
          placeholder={ty.search || 'Search…'}
          defaultValue={search}
          onChange={handleSearchChange}
          aria-label={ty.search} />
      </div>

      {/* Filters toggle */}
      <button className="yaqut-filters-toggle" onClick={() => setFiltersOpen(p => !p)}>
        {filtersOpen ? '▾' : '▸'} {t.yaqut.filtersTitle}
        <span className="yaqut-filter-count">{filtered.length.toLocaleString()} {ty.entries || 'giriş'}</span>
      </button>

      {filtersOpen && (
        <div className="yaqut-filters">
          {/* Arabic Letter */}
          <div className="yaqut-filter-group">
            <label className="yaqut-filter-label">{ty.letter || 'Harf (الحرف)'}</label>
            <div className="yaqut-letter-chips">
              {allLetters.map(lt => (
                <button key={lt}
                  className={`yaqut-letter-chip${selectedLetter === lt ? ' active' : ''}`}
                  onClick={() => setSelectedLetter(selectedLetter === lt ? '' : lt)}>
                  {lt}
                </button>
              ))}
            </div>
          </div>

          {/* Geo Type chips */}
          <div className="yaqut-filter-group">
            <label className="yaqut-filter-label">{ty.geoType || 'Coğrafi Tip'}</label>
            <div className="yaqut-geo-chips">
              {topGeoTypes.map(gt => (
                <button key={gt}
                  className={`yaqut-geo-chip${selectedGeoTypes.has(gt) ? ' active' : ''}`}
                  style={{
                    color: GEO_COLORS[gt] || '#90a4ae',
                    borderColor: selectedGeoTypes.has(gt) ? (GEO_COLORS[gt] || '#90a4ae') : 'transparent'
                  }}
                  onClick={() => toggleGeoType(gt)}>
                  {GEO_ICONS[gt] || '📍'} {lang === 'tr' ? (GEO_TR[gt] || gt) : (GEO_EN[gt] || gt)}
                </button>
              ))}
            </div>
          </div>

          {/* Country */}
          <div className="yaqut-filter-group">
            <label className="yaqut-filter-label">{ty.country || 'Ülke'}</label>
            <select className="yaqut-select" value={selectedCountry}
              onChange={e => setSelectedCountry(e.target.value)}>
              <option value="">{ty.allCountries || 'Tüm Ülkeler'}</option>
              {allCountries.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {/* Historical Period */}
          <div className="yaqut-filter-group">
            <label className="yaqut-filter-label">{ty.historicalPeriod || 'Tarihî Dönem'}</label>
            <div className="yaqut-period-row">
              <button className={`yaqut-period-btn${selectedPeriod === '' ? ' active' : ''}`}
                onClick={() => setSelectedPeriod('')}>{ty.allPeriods || 'Tümü'}</button>
              {periods.map(p => (
                <button key={p}
                  className={`yaqut-period-btn${selectedPeriod === p ? ' active' : ''}`}
                  onClick={() => setSelectedPeriod(selectedPeriod === p ? '' : p)}>
                  {PERIOD_LABEL[p]?.[lang] || p}
                </button>
              ))}
            </div>
          </div>

          {/* Atlas Tags */}
          <div className="yaqut-filter-group">
            <label className="yaqut-filter-label">{ty.atlasTags || 'Etiketler'}</label>
            <div className="yaqut-tag-chips">
              {topTags.slice(0, 15).map(tg => (
                <button key={tg}
                  className={`yaqut-tag-chip${selectedTags.has(tg) ? ' active' : ''}`}
                  onClick={() => toggleTag(tg)}>
                  {tg}
                </button>
              ))}
            </div>
          </div>

          {/* Cross-ref range */}
          <div className="yaqut-filter-group">
            <label className="yaqut-filter-label">{ty.crossRefCount || 'Ziriklî Kişi Sayısı'}</label>
            <div className="yaqut-period-row">
              <button className={`yaqut-period-btn${crossRefRange === '' ? ' active' : ''}`}
                onClick={() => setCrossRefRange('')}>{ty.allRanges || 'Tümü'}</button>
              <button className={`yaqut-period-btn${crossRefRange === '0' ? ' active' : ''}`}
                onClick={() => setCrossRefRange(crossRefRange === '0' ? '' : '0')}>0</button>
              <button className={`yaqut-period-btn${crossRefRange === '1-10' ? ' active' : ''}`}
                onClick={() => setCrossRefRange(crossRefRange === '1-10' ? '' : '1-10')}>1-10</button>
              <button className={`yaqut-period-btn${crossRefRange === '10-50' ? ' active' : ''}`}
                onClick={() => setCrossRefRange(crossRefRange === '10-50' ? '' : '10-50')}>10-50</button>
              <button className={`yaqut-period-btn${crossRefRange === '50+' ? ' active' : ''}`}
                onClick={() => setCrossRefRange(crossRefRange === '50+' ? '' : '50+')}>50+</button>
            </div>
          </div>

          {/* DIA random */}
          <button className="yaqut-random-dia" onClick={() => {
            const diaBios = filtered.filter(e => e.ds);
            if (diaBios.length) {
              const pick = diaBios[Math.floor(Math.random() * diaBios.length)];
              window.open(`https://islamansiklopedisi.org.tr/${pick.ds}`, '_blank');
            }
          }}>
            🎲 {ty.randomDia || 'Rastgele DİA Maddesi'}
          </button>
        </div>
      )}

      {/* Entry list header */}
      <div className="yaqut-list-header">
        {filtered.length.toLocaleString()} {ty.entries || 'giriş'}
        {filtered.length === 0 && <div className="yaqut-no-results">{ty.noEntries || 'Bu filtre ile eşleşen giriş bulunamadı.'}</div>}
      </div>

      <VirtualList
        items={filtered}
        itemHeight={ITEM_HEIGHT}
        className="yaqut-list-container"
        renderItem={(e) => renderYaqutRow(e, selectedId, onSelect, lang)}
      />
    </div>
  );
}

export { GEO_COLORS, GEO_ICONS };
