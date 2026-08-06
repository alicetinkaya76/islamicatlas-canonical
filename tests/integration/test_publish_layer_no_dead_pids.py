"""Gezinme dosyalarında ÖLÜ pid kalmasın (H60).

H49/H50 birleştirmesi 1.364 kişi, daha önceki turlar 241 yer kaydını
yumuşak-sildi. "pid yaşar" ≠ "UI bulur" — bu ders bu depoda DÖRT kez
öğrenildi (H49 isnâd uçları, H55 eser müellifleri, H56 zombi marker'lar,
H60 bu tur) ve her seferinde başka bir katmanda tekrarlandı.

H60'ta tüm yayın katmanı tarandı. Bulunan ve onarılan:

    person_bridge.json     1.398 ölü pid → 0   (el-Aʿlâm/DİA/EI-1 kartından
                                                havuza giden bağın %6'sı
                                                boş ekrana gidiyordu)
    ulema_pool_links.json     12 ölü yer pid → 0  (H49'da kişi uçları
                                                çevrilmiş, YER uçları
                                                atlanmıştı — 457 geçiş)
    visits.json / _meta        7 ölü pid → 0   (biri Evliyâ Çelebi'nin
                                                KENDİSİ, 10 geçiş)
    muqaddasi_atlas_layer    214 → 15 (kalanlar ÇAKIŞMA)
    place_index.json           3 →  2 (kalanlar ÇAKIŞMA)
    place_facets.json          2 →  0
    evliya_atlas_layer         1 →  1 (ÇAKIŞMA)

ÇAKIŞMA NEDİR VE NEDEN ÇÖZÜLMEZ: kazanan pid ZATEN aynı katmanda ayrı bir
satır/anahtar olarak bulunuyor. İkisini birleştirmek bir GÖRÜNTÜ/VERİ
kararıdır — farklı kaynaklardan farklı metin, koordinat ve anılma sayısı
taşıyabilirler. Otomatik birleştirilmez; sayılır ve raporlanır.

`pid_map.json` dosyaları KAPSAM DIŞI: onlar "bu kaynak kaydı hangi pid olarak
mint edildi" kaydıdır. Oradaki eski pid yanlış değil, TARİHTİR; yeniden
yazmak provenansı bozar. Gezinme sorunu ayrı katmanda (person_bridge)
çözülür.
"""

import json
import re
from pathlib import Path

import pytest

from ._store import STORE_SKIP

pytestmark = STORE_SKIP

REPO = Path(__file__).resolve().parents[2]
KOKLER = [REPO / "web" / "public" / "books", REPO / "web" / "public" / "view-data"]
PID_RE = re.compile(r"iac:(person|place|work|event|institution|dynasty)-(\d+)")

# Ölü pid taşıması KABUL EDİLEN dosyalar + gerekçe.
MUAF = {
    "pid_map.json": "kaynak-id → mint edilen pid KAYDI; eski pid tarihtir, provenans",
}
# Çakışma yüzünden çözülemeyen, ölçülmüş üst sınır (kaymayı yakalamak için).
CAKISMA_TAVANI = 30


def _prov_cache():
    c = {}

    def prov(kind, num):
        k = (kind, num)
        if k not in c:
            f = REPO / "data" / "canonical" / kind / f"iac_{kind}_{num:08d}.json"
            try:
                c[k] = json.loads(f.read_text(encoding="utf-8")).get("provenance") or {}
            except (OSError, json.JSONDecodeError):
                c[k] = {}
        return c[k]

    return prov


def _tara():
    prov = _prov_cache()
    sonuc = {}
    for kok in KOKLER:
        if not kok.is_dir():
            continue
        for f in sorted(kok.rglob("*.json")):
            if f.is_symlink() or f.name.endswith(".h60bak"):
                continue
            if any(m in f.name for m in MUAF):
                continue
            try:
                s = f.read_text(encoding="utf-8")
            except OSError:
                continue
            olu = {f"iac:{k}-{n}" for k, n in set(PID_RE.findall(s))
                   if prov(k, int(n)).get("deprecated")}
            if olu:
                sonuc[str(f.relative_to(REPO))] = sorted(olu)
    return sonuc


def test_gezinme_dosyalarinda_olu_pid_tavani_asilmiyor():
    """Kalanlar YALNIZ çakışmalar olmalı; sayı ölçülen tavanı aşmamalı."""
    bulgu = _tara()
    toplam = sum(len(v) for v in bulgu.values())
    assert toplam <= CAKISMA_TAVANI, (
        f"{toplam} ölü pid gezinme katmanında (tavan {CAKISMA_TAVANI}). "
        f"Yeni bir katman yönlendirmeyi atlamış olabilir:\n  "
        + "\n  ".join(f"{k}: {len(v)}" for k, v in sorted(bulgu.items(), key=lambda x: -len(x[1])))
    )


@pytest.mark.parametrize("rel", [
    "web/public/books/person_bridge.json",
    "web/public/view-data/ulema_pool_links.json",
    "web/public/books/visits.json",
    "web/public/books/visits_meta.json",
    "web/public/view-data/place_facets.json",
])
def test_bu_dosyalar_tamamen_temiz(rel):
    """Bunlarda çakışma YOKTU — sıfır olmalı, tolerans yok."""
    p = REPO / rel
    if not p.is_file():
        pytest.skip(f"{rel} yok")
    prov = _prov_cache()
    s = p.read_text(encoding="utf-8")
    olu = sorted({f"iac:{k}-{n}" for k, n in set(PID_RE.findall(s))
                  if prov(k, int(n)).get("deprecated")})
    assert not olu, f"{rel}: {len(olu)} ölü pid — {olu[:5]}"


def test_pid_map_bilerek_muaf():
    """Muafiyet kayıtlı olmalı; sessizce görmezden gelinmemeli."""
    assert "pid_map.json" in MUAF and len(MUAF["pid_map.json"]) > 20


def test_uretici_yonlendirmeyi_yapiyor():
    """Onarım ÜRETİCİDE olmalı — elle düzeltilen dosya bir sonraki koşuda bozulur."""
    kontrol = {
        "pipelines/frontend/build_person_bridge.py": "merge_winner",
        "pipelines/frontend/build_ulema_pool_links.py": "yonlendir_yer",
        "pipelines/frontend/build_view_data.py": "olu_pidleri_cozumle",
        "pipelines/frontend/build_place_facets.py": "kazanan",
        "pipelines/frontend/build_place_index.py": "_kaz",
    }
    eksik = [f for f, isim in kontrol.items()
             if isim not in (REPO / f).read_text(encoding="utf-8")]
    assert not eksik, f"üreticide yönlendirme yok: {eksik}"
