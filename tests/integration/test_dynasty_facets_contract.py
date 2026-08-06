"""Hanedan yayın katmanının sözleşmesi (H57).

H56 denetimi ölçtü: canonical `dynasty` namespace'inin HİÇBİR öz alanı arayüze
çıkmıyordu (`grep web/src` → bosworth_id 0 · had_capital 0 · had_ruler 0 ·
patron_dynasty 0). 186 kayıt, 828 hükümdar ucu, 129 başkent girdisi, 100
ardıllık kenarı ve 457 kurum-himaye bağı yalnızca diskte duruyordu.

BU KATMANIN İKİ KURALI:

  1) YALNIZ v1'DE OLMAYAN ya da v1'DE TIKLANAMAYAN bilgi yayınlanır
     (H54 dersi: v1'de zaten olanı tekrarlama). Ardıllık v1'de HİÇ yok;
     başkent v1'de METİN olarak var ama bağ değil.

  2) ÇÖZÜMÜN NASIL YAPILDIĞI SAKLANMAZ. `had_capital` girdilerinin 64'ü
     birden çok aday arasından İNSAN ONAYI OLMADAN seçilmiş; bunlar
     işaretlenir. Ayrıca çözücünün BAŞLADIĞI ad, vardığı addan farklıysa
     ikisi de taşınır — doğrulanmış vaka: Emevîler'in başkenti kaynakta
     'Şam', çözüm **'Sâm'** (سام), Gûta'da AYRI bir yerleşim (33.5138,
     36.2765 · centroid · ±50 km), Dımaşk (iac:place-00014039) DEĞİL —
     üstelik `status=unique` damgalı. Bu sapma genel bir kuralla
     yakalanamıyor (TR katlamasında iki ad aynı dizeye iniyor), o yüzden
     hüküm verilmez: ikisi de gösterilir.
"""

import json
from pathlib import Path

import pytest

from ._jsutil import yorumsuz

REPO = Path(__file__).resolve().parents[2]
FAC = REPO / "web" / "public" / "view-data" / "dynasty_facets.json"
DB = REPO / "web" / "src" / "data" / "db.json"
PLACE_DIR = REPO / "data" / "canonical" / "place"
POPUP = REPO / "web" / "src" / "components" / "shared" / "PopupFactory.js"
HONESTY = REPO / "web" / "src" / "data" / "dynastyHonesty.js"
MAPVIEW = REPO / "web" / "src" / "components" / "map" / "MapView.jsx"


@pytest.fixture(scope="module")
def fac():
    if not FAC.is_file():
        pytest.skip("dynasty_facets.json yok (üretici koşmamış)")
    return json.loads(FAC.read_text(encoding="utf-8"))


def test_ardillik_yayinlaniyor(fac):
    """v1'de bu bilgi HİÇ yok; katmanın varlık sebebi budur."""
    kenar = sum(len(v.get("onc", [])) + len(v.get("ard", [])) for v in fac["facets"].values())
    assert kenar > 60, f"yalnız {kenar} ardıllık kenarı — canonical bağı kopmuş olabilir"


def test_ardillik_hedefleri_v1de_var(fac):
    """`#dynasty/<id>` açılmayacak bir hedefe bağ VERİLMEZ."""
    if not DB.is_file():
        pytest.skip("db.json yok")
    v1 = {d["id"] for d in json.loads(DB.read_text(encoding="utf-8")).get("dynasties", [])}
    kirik = []
    for k, v in fac["facets"].items():
        for x in v.get("onc", []) + v.get("ard", []):
            if x not in v1:
                kirik.append((k, x))
    assert not kirik, f"v1'de karşılığı olmayan hedefe bağ: {kirik[:5]}"


def test_baskent_hedefleri_yasiyor(fac):
    """Emekli yere bağ verilmez (H49 dersi: 'pid yaşar' ≠ 'UI bulur')."""
    if not PLACE_DIR.is_dir():
        pytest.skip("canonical/place yok")
    kotu = []
    for k, v in fac["facets"].items():
        for b in v.get("bkt", []):
            n = int(str(b["pid"]).rsplit("-", 1)[-1])
            f = PLACE_DIR / f"iac_place_{n:08d}.json"
            if not f.is_file():
                kotu.append((k, b["pid"], "kayıt yok"))
                continue
            if (json.loads(f.read_text(encoding="utf-8")).get("provenance") or {}).get("deprecated"):
                kotu.append((k, b["pid"], "emekli"))
    assert not kotu, f"açılmayan başkent bağı: {kotu[:5]}"


def test_belirsiz_cozumler_isaretli(fac):
    """129 girdinin 64'ü aday arasından ONAYSIZ seçilmiş; bu SÖYLENMELİ."""
    belirsiz = sum(1 for v in fac["facets"].values()
                   for b in v.get("bkt", []) if b.get("belirsiz"))
    assert belirsiz > 40, (
        f"yalnız {belirsiz} girdi belirsiz işaretli — işaret kaybolmuş olabilir"
    )


def test_kaynak_adi_sapmasi_tasiniyor(fac):
    """Çözücünün başladığı ad, vardığı addan farklıysa gösterilmeli."""
    sapma = [(k, b["kn"], b["tr"]) for k, v in fac["facets"].items()
             for b in v.get("bkt", []) if b.get("kn")]
    assert sapma, "hiçbir ad sapması taşınmıyor"
    # Doğrulanmış vaka bu listede OLMALI: 'Şam' → 'Sâm'
    sam = [x for x in sapma if x[1] == "Şam" and x[2] == "Sâm"]
    assert sam, "doğrulanmış 'Şam' → 'Sâm' sapması kaybolmuş — ölçüm değişmiş olabilir"


def test_dynasty_subtype_yayinlanmiyor(fac):
    """ÖLÇÜLDÜ: 'sultanate' etiketli 35 kaydın 12'si v1'de HANLIK, 7'si ŞAHLIK.
    v1'in `gov` alanı daha ince ve zaten ekranda; kaba etiketi yaymak yanlış."""
    suclu = [k for k, v in fac["facets"].items() if "subtype" in v or "alt_tur" in v]
    assert not suclu, f"kaba alt tür yayına sızmış: {suclu[:5]}"


def test_himaye_sayisi_var(fac):
    """457 kurum patron_dynasty ile bir hanedana bağlı; v1'de bu bağ yok."""
    toplam = sum(v.get("kurum", 0) for v in fac["facets"].values())
    assert toplam > 400, f"himaye toplamı {toplam} — bağ kopmuş olabilir"


# ── Arayüz sözleşmesi ──────────────────────────────────────────────────────

def test_popup_canonical_blogu_basiyor():
    s = yorumsuz(POPUP.read_text(encoding="utf-8"))
    assert "dynastyFacets" in s, "popup canonical bağları hiç okumuyor"
    assert "p-canon" in s, "canonical blok v1 satırlarından ayrılmıyor"
    assert "b.kn" in s, "kaynak adı sapması ekrana basılmıyor"
    assert "b.belirsiz" in s, "onaysız çözüm işareti ekrana basılmıyor"


def test_tembel_veri_gec_gelirse_blok_kaybolmuyor():
    """Popup HTML'i STATİK bir dize; veri sonradan gelirse blok hiç basılmazdı.
    Ölçüldü: temiz yüklemede `.p-canon` yoktu. Abonelik bir kez yeniden
    çizim tetikler."""
    h = yorumsuz(HONESTY.read_text(encoding="utf-8"))
    assert "onDynastyDataReady" in h, "veri-hazır bildirimi yok"
    m = yorumsuz(MAPVIEW.read_text(encoding="utf-8"))
    assert "onDynastyDataReady" in m, "MapView bildirime abone değil"
    assert "canonHazir" in m, "yeniden çizim tetikleyicisi bağımlılıkta yok"
