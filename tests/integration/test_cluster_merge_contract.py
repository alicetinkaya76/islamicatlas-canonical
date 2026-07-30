"""H49 guard — birleştirme SİLME DEĞİL, yönlendirmedir.

Bu, deponun tek gerçek veri-yıkıcı işlemi. Sözleşme:
  1) Kaybeden pid'in canonical dosyası YAŞAMAYA DEVAM EDER (atıf istikrarı).
     Bir gün biri "temizlik" diye dosyaları silerse bu test kırmızı yanar.
  2) Her kaybeden `deprecated: true` + `deprecated_in_favor_of` taşır.
  3) Yönlendirilen kazanan GERÇEKTEN var ve kendisi deprecated DEĞİL
     (zincirleme yönlendirme = kırık bağ).
  4) Gerekçe `record_history`de kayıtlı — gerekçesiz karar denetlenemez.
  5) Birleşen her küme yargı defterinde 'evet' kararına dayanır. Yargısız
     birleştirme yasak: ölçüldü, otomatik ölçüt olası katmanda %14, zayıf
     katmanda %50 yanlış veriyor.
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / "data" / "_state" / "h49_cluster_merge.json"
JUDGE = REPO / "data" / "_state" / "person_cluster_judgments.json"
PERSON = REPO / "data" / "canonical" / "person"

pytestmark = pytest.mark.skipif(not LEDGER.is_file(), reason="birleştirme koşulmamış")


@pytest.fixture(scope="module")
def led():
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def _rec(pid: str):
    p = PERSON / f"iac_person_{int(pid.rsplit('-', 1)[-1]):08d}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def test_kaybeden_kayitlar_yasiyor(led):
    """SİLME YASAK: yumuşak-silinen pid'in dosyası duruyor olmalı."""
    kayip = [k for m in led["merges"] for k in m["kaybedenler"] if _rec(k) is None]
    assert not kayip, f"kaybeden kaydın dosyası YOK (silinmiş?): {kayip[:5]}"


def test_kaybedenler_dogru_isaretli(led):
    hatali = []
    for m in led["merges"]:
        for k in m["kaybedenler"]:
            prov = (_rec(k) or {}).get("provenance") or {}
            if not prov.get("deprecated"):
                hatali.append(f"{k}: deprecated değil")
            elif prov.get("deprecated_in_favor_of") != m["kazanan"]:
                hatali.append(f"{k}: yönlendirme yanlış ({prov.get('deprecated_in_favor_of')})")
    assert not hatali, hatali[:5]


def test_kazananlar_canli_ve_zincirleme_yok(led):
    """Kazanan da deprecated olursa bağ zincirlenir ve boşa çıkar."""
    hatali = []
    for m in led["merges"]:
        r = _rec(m["kazanan"])
        if r is None:
            hatali.append(f"{m['kazanan']}: kazanan kaydı YOK")
        elif (r.get("provenance") or {}).get("deprecated"):
            hatali.append(f"{m['kazanan']}: kazanan da deprecated (zincirleme)")
    assert not hatali, hatali[:5]


def test_gerekce_kayitli(led):
    hatali = []
    for m in led["merges"]:
        for k in m["kaybedenler"]:
            hist = ((_rec(k) or {}).get("provenance") or {}).get("record_history") or []
            # Göç kimliği note'un başında: şema record_history'ye özel alan
            # eklemeye izin vermiyor (additionalProperties:false) — H31'de
            # öğrenilen kural, burada da geçerli.
            if not any("[h49_001]" in (h.get("note") or "") for h in hist):
                hatali.append(k)
    assert not hatali, f"gerekçesi record_history'de olmayan kayıt: {hatali[:5]}"


@pytest.mark.skipif(not JUDGE.is_file(), reason="yargı defteri yok")
def test_yargisiz_birlestirme_yok(led):
    """Her birleşme, iki merceğin 'aynı kişi' kararına dayanmalı."""
    yargi = json.loads(JUDGE.read_text(encoding="utf-8"))["kararlar"]
    kacak = [m["kume_id"] for m in led["merges"]
             if (yargi.get(m["kume_id"]) or {}).get("karar") != "evet"]
    assert not kacak, f"yargısı 'evet' olmayan küme birleştirilmiş: {kacak[:5]}"


def test_geri_alma_yolu_duruyor():
    """--restore olmadan bu işlem geri alınamaz; kod yolunun varlığı kilitli."""
    src = (REPO / "pipelines" / "migrations" / "h49_001_cluster_merge.py").read_text(encoding="utf-8")
    assert "--restore" in src and "deprecated_in_favor_of" in src, \
        "geri alma yolu kaybolmuş"


def test_yonlendirme_hedefleri_havuzda(led):
    """ATIF İSTİKRARI: her yönlendirme hedefi havuzda BULUNABİLİR olmalı.

    Yumuşak-silinen pid havuzda görünmez; eski bağ (kitap müellifi, paylaşılmış
    derin link) yönlendirme olmadan boş ekrana düşer. ÖLÇÜLDÜ: birleştirmeden
    hemen sonra 17 kitabın 5'inin müellif bağı kopmuştu. Bu test, yönlendirmenin
    her zaman CANLI bir kayda çıktığını kilitler.
    """
    redir_p = REPO / "web" / "public" / "view-data" / "person_redirects.json"
    pool_p = REPO / "web" / "public" / "books" / "ulema_pool.json"
    if not (redir_p.is_file() and pool_p.is_file()):
        pytest.skip("yönlendirme ya da havuz üretilmemiş")
    redir = json.loads(redir_p.read_text(encoding="utf-8"))["redirects"]
    havuz = {r["id"] for r in json.loads(pool_p.read_text(encoding="utf-8"))["kisiler"]}
    kirik = {k: v for k, v in redir.items() if int(v) not in havuz}
    assert not kirik, f"yönlendirme hedefi havuzda yok: {list(kirik.items())[:5]}"
    # Ledger'daki her kaybeden için yönlendirme kaydı olmalı
    eksik = [k for m in led["merges"] for k in m["kaybedenler"]
             if str(int(k.rsplit("-", 1)[-1])) not in redir]
    assert not eksik, f"yönlendirmesi olmayan kaybeden: {eksik[:5]}"


def test_ui_yonlendirmeyi_uyguluyor():
    ui = (REPO / "web" / "src" / "components" / "scholars" / "UlemaPool.jsx").read_text(encoding="utf-8")
    assert "person_redirects.json" in ui and "redirects[String(" in ui, \
        "UlemaPool yönlendirmeyi uygulamıyor — eski linkler boş ekrana düşer"
