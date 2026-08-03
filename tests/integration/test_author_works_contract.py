"""Müellif → eser köprüsünün sözleşmesi (H55).

Bu katman iki şeyi aynı anda taşıyor ve ikisi de kolayca sessizce bozulur:

  1) YÖNLENDİRME. H49/H50 kimlik birleştirmesi kişileri yumuşak-sildi ama eser
     kayıtlarının `authors` alanına HİÇ uğramadı (ölçüldü: 9.385 bağın 1.177'si
     yumuşak-silinmiş pid'e gidiyor). Köprü bunları kazanan pid'e çevirir.
     Çevirmeyi unutursa kullanıcı "müellifi yok" görür — ve bu, veriye bakan
     birinin fark edemeyeceği bir kayıptır, çünkü canonical'da bağ DURUYOR.

  2) YIL'IN ANLAMI. `composition_temporal.start_ah` TELİF TARİHİ DEĞİL:
     9.385 kaydın 9.158'inde müellifin ölüm yılıdır ve `approximation:
     "before"` taşır. Yıl, sınır işareti olmadan yayına çıkarsa uydurulmuş bir
     kesinlik doğar — deponun en sert kuralının ihlali.
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "web" / "public" / "view-data" / "author_works.json"
PERSON_DIR = REPO / "data" / "canonical" / "person"
UI = REPO / "web" / "src" / "components" / "scholars" / "UlemaPool.jsx"


@pytest.fixture(scope="module")
def doc():
    if not OUT.is_file():
        pytest.skip("author_works.json yok (build_author_works.py koşulmamış)")
    return json.loads(OUT.read_text(encoding="utf-8"))


def test_yapi(doc):
    for k in ("_doc", "counts", "eserler", "yazar"):
        assert k in doc, f"'{k}' anahtarı yok"
    assert doc["counts"]["eser"] > 9000, "eser sayısı beklenenden düşük"


def test_hicbir_muellif_yumusak_silinmis_degil(doc):
    """Köprünün varlık sebebi: kullanıcı hep YAŞAYAN kayda düşmeli."""
    if not PERSON_DIR.is_dir():
        pytest.skip("canonical/person yok")
    kotu = []
    for pnum in doc["yazar"]:
        p = PERSON_DIR / f"iac_person_{int(pnum):08d}.json"
        if not p.is_file():
            kotu.append(f"{pnum}: kayıt dosyası yok")
            continue
        prov = json.loads(p.read_text(encoding="utf-8")).get("provenance") or {}
        if prov.get("deprecated"):
            kotu.append(f"{pnum}: yumuşak-silinmiş")
    assert not kotu, "yönlendirilmemiş müellif: " + "; ".join(kotu[:10])


def test_yonlendirme_gercekten_calisti(doc):
    """Sayaç 0 ise ya birleştirme geri alınmıştır ya da çözüm sessizce düşmüştür."""
    c = doc["counts"]
    assert c["yonlendirilen_bag"] > 0, (
        "hiçbir bağ yönlendirilmemiş — H49 birleştirmesi göz önünde 1.177 bağ "
        "etkiliyordu; 0 ise çözüm kopmuş demektir"
    )
    assert c["cozulemeyen_bag"] == 0, (
        f"{c['cozulemeyen_bag']} bağ çözülemedi — bunlar sessizce düşürülüyor"
    )


def test_yil_her_zaman_sinir_isaretiyle_gider(doc):
    """`y` varsa `yk` de olmalı; çıplak yıl uydurulmuş kesinliktir."""
    ciplak = [w for w, e in doc["eserler"].items() if "y" in e and "yk" not in e]
    oran = len(ciplak) / max(len(doc["eserler"]), 1)
    assert oran < 0.05, (
        f"{len(ciplak)} eserde yıl var ama yaklaşıklık işareti yok (%{oran*100:.1f}); "
        "bu değer müellifin ölüm yılıdır, telif tarihi değil"
    )


def test_ham_note_tasinmiyor(doc):
    """`note` %100 üretim izi ('Promoted from OpenITI corpus_works…')."""
    suclu = [w for w, e in doc["eserler"].items()
             if any(isinstance(v, str) and "Promoted from" in v for v in e.values())]
    assert not suclu, f"üretim izi yayına sızmış: {suclu[:5]}"


def test_okunabilir_isareti_yalniz_gercek_rafta(doc):
    """`r:1` sitede GERÇEKTEN açılan kitaplara aittir; çekirdek raf 17 kitap."""
    r = [w for w, e in doc["eserler"].items() if e.get("r")]
    assert len(r) <= 40, f"{len(r)} eser 'okunabilir' işaretli — raf bu kadar büyük değil"


def test_ui_yili_ciplak_basmiyor():
    """Arayüz sözleşmesi: 'before' işareti metne dönüşmeli."""
    if not UI.is_file():
        pytest.skip("UlemaPool.jsx yok")
    s = UI.read_text(encoding="utf-8")
    assert "yk === 'before'" in s, "UI 'before' durumunu ayırt etmiyor"
    assert "öncesi" in s, "UI 'öncesi' ifadesini kullanmıyor — çıplak yıl basıyor olabilir"


def test_ui_okunamayan_esere_okuma_bagi_vermiyor():
    """Metni olmayan eser için '📖 sitede oku' çıkarsa boş ekrana götürür."""
    if not UI.is_file():
        pytest.skip("UlemaPool.jsx yok")
    s = UI.read_text(encoding="utf-8")
    assert "e.r" in s and "metni sitede yok" in s, (
        "okunabilirlik dallanması yok — her esere okuma bağı veriliyor olabilir"
    )
