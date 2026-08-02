#!/usr/bin/env bash
# İslam Atlası v2 — yerel test başlatıcı (H15)
# Kullanım: bash scripts/start_local.sh
set -e
REPO="/Users/alicetinkaya/Desktop/islamicatlas_canonical"
cd "$REPO"

echo "▸ 1/3  Typesense (arama motoru) başlatılıyor…"
if ! docker ps --format '{{.Names}}' | grep -q '^islamicatlas-typesense$'; then
  docker start islamicatlas-typesense 2>/dev/null || {
    echo "  (ilk kez) container oluşturuluyor…"
    KEY=$(grep TYPESENSE_API_KEY .env | cut -d= -f2)
    docker run -d --name islamicatlas-typesense --restart unless-stopped \
      -p 8108:8108 -v "$REPO/data/_local/typesense:/data" \
      typesense/typesense:29.0 --data-dir /data --api-key="$KEY" --enable-cors
  }
fi
until curl -s http://localhost:8108/health | grep -q ok; do sleep 1; done
echo "  ✓ Typesense hazır (http://localhost:8108)"

echo "▸ 2/3  Arama verisi güncel mi kontrol ediliyor…"
set -a; source .env; set +a
COUNT=$(curl -s "http://localhost:8108/collections/iac_entities" \
  -H "X-TYPESENSE-API-KEY: $TYPESENSE_API_KEY" 2>/dev/null | grep -o '"num_documents":[0-9]*' | cut -d: -f2)
if [ -z "$COUNT" ] || [ "$COUNT" -lt 1000 ]; then
  echo "  veri yükleniyor (bir kerelik, ~1 dk)…"
  python3 pipelines/search/upsert.py --recreate
else
  echo "  ✓ $COUNT kayıt yüklü"
fi

echo "▸ 3/4  Görünüm verisi canonical'dan üretiliyor (H23; ~5 sn)…"
python3 pipelines/frontend/build_view_data.py --view all | sed 's/^/  /'
python3 pipelines/frontend/build_book_city_atlas.py | sed 's/^/  /'   # H25: kitap→şehir atlasları (Mekke/Bağdat/Şam)
python3 pipelines/frontend/build_canonical_map_layer.py | sed 's/^/  /'   # H26: ana haritaya canonical olay katmanı
python3 pipelines/_index/build_lookup.py --quiet   # H31: indeks bayatlamasın (havuz kaynak izleri)
python3 pipelines/frontend/build_alatli_synchronic.py | sed 's/^/  /'   # H30: Alatlı senkronik atlas
python3 pipelines/frontend/build_scholar_network.py | sed 's/^/  /'   # H34: canonical isnâd ağı
python3 pipelines/frontend/build_ulema_pool.py | sed 's/^/  /' | tail -2   # H29: havuz bayatlamasın (yeni kişi mint'leri)
python3 pipelines/frontend/build_place_facets.py | sed 's/^/  /'   # H54: yer olguları (alan + note ayıklaması)
python3 pipelines/frontend/build_darp_pids.py | sed 's/^/  /'   # H53: darphane → yer pid köprüsü
python3 pipelines/frontend/build_person_clusters.py | sed 's/^/  /'   # H47: aynı-kişi kümeleri
python3 pipelines/frontend/build_person_bridge.py | sed 's/^/  /'   # H45: kişi köprüsü (alam/dia/ei1)
python3 pipelines/frontend/build_ulema_pool_links.py | sed 's/^/  /'   # H44: havuz ilişki+not yan dosyaları
python3 pipelines/frontend/build_causal_review.py | sed 's/^/  /'   # H37: nedensellik onay kuyruğu + okuyucu köprüsü
python3 pipelines/frontend/build_canonical_overview.py | sed 's/^/  /'   # H28: Pano canonical özeti
echo "  ✓ web/public/view-data/ güncel (eski görünümler artık merkezî defterden)"

echo "▸ 4/4  Web arayüzü başlatılıyor…"
echo ""
echo "  ►►►  http://localhost:3000  ◄◄◄"
echo ""
echo "  (durdurmak için Ctrl+C)"
cd web && npm run dev -- --port 3000 --no-open
