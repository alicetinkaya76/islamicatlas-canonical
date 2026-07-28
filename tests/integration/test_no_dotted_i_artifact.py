"""H31 guard — "noktalı i" artefaktı geri gelmesin.

Kök neden: Türkçe-duyarsız `str.title()`/`.lower()` → "İ" (U+0130) yerine
"i"+U+0307 üretir. Küçük "i+nokta"nın birleşik hâli Unicode'da YOK, bu yüzden
NFC bunu düzeltmez; arama token'ını kırar (H29: "Fatma Aliye" aktif kaydı
bulunamıyordu). 1.274 kayıt h31_001 ile onarıldı; üretim noktaları `tr_title()`
kullanacak şekilde düzeltildi.

Bu test iki şeyi kilitler:
  1) canonical etiket alanlarında artefakt YOK (regresyon olursa kırmızı),
  2) üretim kodunda çıplak `.title()` KULLANILMAZ (tr_title kullanılmalı).
"""
import ast
import glob
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
DOTTED = "i̇"          # "i" + U+0307
TEXT_KEYS = {"labels", "note", "nisba", "laqab", "kunya", "nasab", "profession"}
NAMESPACES = ["person", "place", "work", "dynasty", "event", "institution"]


def _has_dotted(v) -> bool:
    if isinstance(v, str):
        return DOTTED in v
    if isinstance(v, list):
        return any(_has_dotted(x) for x in v)
    if isinstance(v, dict):
        return any(_has_dotted(x) for x in v.values())
    return False


def test_canonical_labels_have_no_dotted_i():
    """Etiket/metin alanlarında 'i'+U+0307 kalmamalı."""
    offenders = []
    for ns in NAMESPACES:
        for f in glob.glob(str(REPO / "data" / "canonical" / ns / "*.json")):
            txt = pathlib.Path(f).read_text(encoding="utf-8")
            if DOTTED not in txt:
                continue                      # hızlı çıkış
            rec = json.loads(txt)
            for k in TEXT_KEYS & set(rec):
                if _has_dotted(rec[k]):
                    offenders.append(f"{rec.get('@id')}::{k}")
    assert not offenders, (
        f"{len(offenders)} kayıtta 'noktalı i' artefaktı var (ilk 5: "
        f"{offenders[:5]}). Onarım: "
        f"python3 pipelines/migrations/h31_001_dotted_i_repair.py --apply"
    )


def test_pipelines_do_not_use_bare_title():
    """Üretim kodu çıplak .title() ÇAĞIRMAMALI — tr_title() Türkçe-güvenli.

    AST ile bakılır: docstring/yorumda geçen '.title()' METNİ sayılmaz, yalnız
    gerçek çağrı düğümleri (ör. `t.title()`) yakalanır."""
    hits = []
    for f in glob.glob(str(REPO / "pipelines" / "**" / "*.py"), recursive=True):
        p = pathlib.Path(f)
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:                      # derlenmeyen dosya testin konusu değil
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "title"
                    and not node.args):
                hits.append(f"{p.relative_to(REPO)}:{node.lineno}")
    assert not hits, (
        "Çıplak .title() Türkçe 'İ'yi bozar ('ABDÜLLATİF'→'Abdüllati̇f'). "
        f"tr_title() kullanın. Bulunanlar: {hits}"
    )
