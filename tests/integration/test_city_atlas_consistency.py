"""H27 oto-uyum guard'ı — kitap-türevi şehir atlaslarının ÇİFT-KAYIT tutarlılığı.

Denetim bulgusu: şehir atlası eklemek İKİ elle liste ister ve lockstep
güncellenmeli — `pipelines/frontend/build_book_city_atlas.py` CITIES (üretici)
ile `web/src/data/cityAtlasRegistry.js` (UI kaydı). Biri güncellenip diğeri
unutulursa SESSİZ kırılır (iğneleme/rozet/kitap-kabı sekmesi bozulur).

Bu test o sessiz driftı GÜRÜLTÜLÜ yapar: iki liste birbirini tam karşılamazsa
suite kırmızıya döner. (Tam tek-kaynağa geçilene dek güvenlik ağı.)
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pipelines.frontend.build_book_city_atlas import CITIES  # noqa: E402

REGISTRY = REPO / "web" / "src" / "data" / "cityAtlasRegistry.js"


def _registry_book_cities():
    """Registry'den bookPidnum taşıyan (kitap-türevi) şehir girdilerini çıkar.
    Dönüş: {city_id: {"bookPidnum": str, "dataFile": str}}."""
    text = REGISTRY.read_text(encoding="utf-8")
    # Her nesne bloğunu 'id:' ile ayır; bookPidnum içerenleri topla.
    out = {}
    # id: 'x' ... sonraki id:'e kadar olan pencerede bookPidnum/dataFile ara.
    ids = list(re.finditer(r"id:\s*'([a-z0-9_-]+)'", text))
    for i, m in enumerate(ids):
        start = m.start()
        end = ids[i + 1].start() if i + 1 < len(ids) else len(text)
        block = text[start:end]
        bp = re.search(r"bookPidnum:\s*'(\d+)'", block)
        if not bp:
            continue
        df = re.search(r"dataFile:\s*'([^']+)'", block)
        out[m.group(1)] = {
            "bookPidnum": bp.group(1),
            "dataFile": df.group(1) if df else None,
        }
    return out


def test_cities_and_registry_agree():
    """CITIES (üretici) ↔ registry kitap-şehirleri birebir örtüşmeli."""
    gen = {c["city_id"]: c["pidnum"] for c in CITIES}
    reg = _registry_book_cities()

    # 1) Üreticideki her şehir registry'de olmalı, aynı pidnum ile.
    for city_id, pidnum in gen.items():
        assert city_id in reg, (
            f"'{city_id}' build_book_city_atlas.CITIES'te var ama "
            f"cityAtlasRegistry.js'de bookPidnum'lu girdi YOK — çift-kayıt driftı."
        )
        assert reg[city_id]["bookPidnum"] == pidnum, (
            f"'{city_id}' pidnum uyuşmuyor: üretici={pidnum} "
            f"registry={reg[city_id]['bookPidnum']}."
        )
        assert reg[city_id]["dataFile"] == f"/view-data/city-atlas/{city_id}.json", (
            f"'{city_id}' dataFile beklenenden farklı: {reg[city_id]['dataFile']}."
        )

    # 2) Registry'deki her kitap-şehri üreticide olmalı (yoksa üretilmez → boş).
    for city_id in reg:
        assert city_id in gen, (
            f"'{city_id}' cityAtlasRegistry.js'de bookPidnum'lu ama "
            f"build_book_city_atlas.CITIES'te YOK — veri hiç üretilmez."
        )
