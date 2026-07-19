# Hafta 11 · Stage 8 — İslam Atlası v2 web arayüzü (v0 ÇALIŞIYOR)

**Tarih:** 2026-07-13 · **Önkoşul:** S7 (yerel Typesense, 56,399 kayıt)

Kullanıcı direktifi "yeni siteyi de sen yapacaksın" uyarınca `web/` altında
framework'süz statik v0 kuruldu ve tarayıcıda uçtan uca doğrulandı:

- **Arama sayfası:** yazarken-ara (180 ms debounce), facet'ler (Tür /
  Kaynak katmanı / Alt tür / Hicrî yüzyıl — hepsi TR etiketli), sonuç
  kartlarında tür çipi + AR ad + yıl + katman çipleri + 📍, vurgulama,
  sayfalama. 56.399 kayıt, tipik sorgu < 10 ms.
- **Varlık sayfası:** üç-dilli başlık, tasvirler (tr/en/ar, RTL), diğer
  adlar, künye, Leaflet haritası, ilişkili varlıklar (projeksiyondaki
  related_pids → tıklanabilir zincir; Alâeddin Camii → Iconium doğrulandı).
- **Güvenlik:** tarayıcıya yalnız search-only anahtar gider (web/config.js,
  gitignored); admin anahtarı .env'de.
- **Sunucu:** web/serve.mjs (node, sıfır bağımlılık) — preview sandbox'ında
  pyenv/CLT-python codec hatası verdi, node temiz.
- **Düzeltmeler:** Typesense id filtresi TIRNAKSIZ ister (çift-tırnak 0
  sonuç, canlıya karşı doğrulandı); subtypes facet'i tüm tiplerde ortak →
  kişi/olay alt-tür çevirileri eklendi, başlık "Alt tür".

Doğrulama: ekran görüntüleri ile arama + facet + varlık + harita akışı;
"Alâeddin Camii" kaydında iki kaynak katmanı çipi (evliya-celebi +
konya-city-atlas) — S6 augment'inin kullanıcıya görünen kanıtı.
