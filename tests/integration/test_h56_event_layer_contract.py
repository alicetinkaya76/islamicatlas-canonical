"""Olay katmanı ve arama projeksiyonu sözleşmesi (H56, ikinci dalga).

Üç ayrı kusur kilitleniyor; üçü de denetimde ölçüldü:

  1) SAYI İLE İÇERİK ÇELİŞİYORDU. Üreticide CAP=25, arayüzde slice(0,12).
     Bağdat marker'ı "388 canonical olay" yazıp 12 satır gösteriyor, sonra
     hedefsiz bir "+376 daha" satırı basıyordu. 5.618 olayın yalnız 2.616'sı
     (%46) ekrana ulaşıyordu.

  2) KOORDİNAT BELİRSİZLİĞİ YAYINA HİÇ TAŞINMIYORDU. Kaynak kayıt
     `coords.uncertainty` ve `precision_meters` taşıyor (18.411 yerde dolu),
     üretici hiçbirini okumuyordu: 250 km hassasiyetli bir nokta, 100 m'lik
     bir şehirle aynı görsel kesinlikte çiziliyordu.

  3) ARAMA PROJEKSİYONU ÜRETİM İZİ YAYINLIYORDU. `description_en: $.note`
     — 9.956 dokümanın %100'ü en az bir boru hattı belirteci taşıyordu
     (`Kaynak:` 9.102, `dup-cluster` 2.917, `Çıkarım güveni` 9.102).
     Hosting açıldığı an dahilî notlar kamuya çıkacaktı.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
LAYER = REPO / "web" / "public" / "view-data" / "canonical_events.json"
PRODUCER = REPO / "pipelines" / "frontend" / "build_canonical_map_layer.py"
UI = REPO / "web" / "src" / "components" / "map" / "CanonicalLayer.jsx"
PROJ_DIR = REPO / "search" / "projections"
PLACE_DIR = REPO / "data" / "canonical" / "place"

URETIM_IZI = re.compile(r"Kaynak:|Çıkarım güveni|dup-cluster|v1 tip:|Promoted from|Tier-\d")


@pytest.fixture(scope="module")
def katman():
    if not LAYER.is_file():
        pytest.skip("canonical_events.json yok (üretici koşmamış)")
    return json.loads(LAYER.read_text(encoding="utf-8"))


# ── 1) Kesme yok: başlıktaki sayı listedeki satırla aynı ───────────────────

def test_payload_kesilmemis(katman):
    kesik = [(p["pid"], p["count"], len(p["events"]))
             for p in katman if len(p["events"]) != p["count"]]
    assert not kesik, (
        "count ile events uzunluğu tutmuyor — popup gösteremediği bir sayı "
        f"yazacak: {kesik[:5]}"
    )


def test_ui_listeyi_kesmiyor():
    s = UI.read_text(encoding="utf-8")
    assert "p.events.slice(" not in s, "arayüz olay listesini yeniden kesiyor"
    assert "overflow-y" in s, "uzun liste kaydırılamıyor (kesme yerine kaydırma şartı)"


def test_sahte_daha_satiri_yok():
    """'+N daha' hedefsizdi; kesme kalktığına göre hiç çıkmamalı."""
    s = UI.read_text(encoding="utf-8")
    assert "p.count - 12" not in s, "eski sahte '+N daha' hesabı geri gelmiş"


def test_yogun_yer_tam_tasiniyor(katman):
    en_yogun = max(katman, key=lambda p: p["count"])
    assert len(en_yogun["events"]) == en_yogun["count"], (
        f"{en_yogun.get('name_tr')} {en_yogun['count']} olay bildiriyor ama "
        f"{len(en_yogun['events'])} taşıyor"
    )
    assert en_yogun["count"] > 100, "ölçüm değişmiş: en yoğun yer beklenenden küçük"


# ── 2) Koordinat belirsizliği yayına çıkıyor ───────────────────────────────

def test_belirsizlik_payloadda(katman):
    u_olan = [p for p in katman if p.get("u")]
    assert len(u_olan) > len(katman) * 0.5, (
        f"{len(u_olan)}/{len(katman)} marker belirsizlik kodu taşıyor — "
        "kaynak kayıtların çoğunda bu bilgi VAR, taşınmıyor demektir"
    )
    belirsiz = [p for p in katman if p.get("u") in ("c", "a")]
    assert belirsiz, "hiçbir marker belirsiz işaretlenmemiş"


def test_belirsizlik_kaynak_kayitla_tutarli(katman):
    """Bayrak uydurulmamalı: marker'ın kodu place kaydından gelmeli."""
    if not PLACE_DIR.is_dir():
        pytest.skip("canonical/place yok")
    kod = {"exact": "e", "approximate": "a", "centroid": "c"}
    hatali = []
    for p in katman[:400]:
        num = int(str(p["pid"]).rsplit("-", 1)[-1])
        f = PLACE_DIR / f"iac_place_{num:08d}.json"
        if not f.is_file():
            continue
        c = (json.loads(f.read_text(encoding="utf-8")).get("coords") or {})
        u = c.get("uncertainty")
        beklenen = kod.get(u.get("type") if isinstance(u, dict) else u)
        if p.get("u") != beklenen:
            hatali.append((p["pid"], p.get("u"), beklenen))
    assert not hatali, f"belirsizlik kodu kaynakla uyuşmuyor: {hatali[:5]}"


def test_ui_belirsizligi_gosteriyor():
    s = UI.read_text(encoding="utf-8")
    assert "belirsizlikMetni" in s, "arayüz belirsizliği hiç okumuyor"
    assert "dashArray" in s, "belirsiz marker görsel olarak ayrılmıyor"


# ── 3) Emekli yere bağlanma ────────────────────────────────────────────────

def test_emekli_yere_marker_yok(katman):
    if not PLACE_DIR.is_dir():
        pytest.skip("canonical/place yok")
    zombi = []
    for p in katman:
        num = int(str(p["pid"]).rsplit("-", 1)[-1])
        f = PLACE_DIR / f"iac_place_{num:08d}.json"
        if not f.is_file():
            continue
        prov = json.loads(f.read_text(encoding="utf-8")).get("provenance") or {}
        if prov.get("deprecated"):
            zombi.append(p["pid"])
    assert not zombi, f"yumuşak-silinmiş yere marker basılıyor: {zombi}"


def test_uretici_yonlendirme_yapiyor():
    s = PRODUCER.read_text(encoding="utf-8")
    assert "deprecated_in_favor_of" in s, "olay location'ı halefe çözülmüyor"


# ── 4) Alt tür uydurulmuyor ────────────────────────────────────────────────

def test_event_alt_turu_uydurulmuyor(katman):
    """Alt türü olmayan kayda "Event" yazmak, 'tür yok'u bir TÜR gibi
    gösteriyordu (1.838 kayıt)."""
    suclu = [p["pid"] for p in katman
             if any(e.get("subtype") == "Event" for e in p["events"])]
    assert not suclu, f"'Event' sahte alt türü geri gelmiş: {suclu[:5]}"


# ── 5) Arama projeksiyonu üretim izi yayınlamıyor ──────────────────────────

def test_hicbir_projeksiyon_note_yayinlamiyor():
    if not PROJ_DIR.is_dir():
        pytest.skip("search/projections yok")
    suclu = []
    for f in sorted(PROJ_DIR.glob("*.yaml")):
        m = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for alan, kaynak in (m.get("mappings") or {}).items():
            if alan.startswith("description_") and kaynak == "$.note":
                suclu.append(f"{f.name}:{alan}")
    assert not suclu, (
        "açıklama alanı ham `note`'a bağlı — note üretim izi taşır ve "
        f"yayınlanırsa dahilî kayıt kamuya çıkar: {suclu}"
    )


def test_event_projeksiyonu_uc_dili_de_bagliyor():
    f = PROJ_DIR / "event.yaml"
    if not f.is_file():
        pytest.skip("event.yaml yok")
    m = (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("mappings") or {}
    for dil in ("en", "tr", "ar"):
        assert m.get(f"description_{dil}") == f"$.labels.description.{dil}", (
            f"description_{dil} doğru kaynağa bağlı değil: {m.get(f'description_{dil}')}"
        )
