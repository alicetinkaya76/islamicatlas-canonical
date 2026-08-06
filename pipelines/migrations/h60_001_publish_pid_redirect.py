#!/usr/bin/env python3
"""Yayın katmanındaki ÖLÜ pid'leri kazanana çevirir — cerrahi (H60).

SORUN: H49/H50 birleştirmesi 1.364 kişi kaydını, daha önceki turlar da 241
yer kaydını yumuşak-sildi. Yayın katmanının bir kısmı hâlâ birleştirmeden
ÖNCEKİ pid'leri taşıyor. Ölçüldü — `visits.json` (20 Temmuz'dan beri
dokunulmamış):

    iac:person-00000223 'Evliyâ Çelebi'      → iac:person-00002620  (10 geçiş)
    iac:place-00013267  'er-Rahbe'           → iac:place-00015073   ( 1 geçiş)
    iac:place-00017660  'Sebeşvaroş (Sebeș)' → iac:place-00017588   ( 1 geçiş)

Seyahat katmanının ÖZNESİ olan Evliyâ Çelebi'nin pid'i ölü; o pid'le havuza
gitmeye çalışan her bağ boş ekrana düşer.

NEDEN ÜRETİCİ KOŞTURULMUYOR: `build_visits.py` bir TASLAK üretir ve çıktısı
insan onay kuyruğuna girer (H21). Yeniden koşturmak onaylanmış taslağı
ezerdi. Bu script yalnız ÖLÜ PİD DİZELERİNİ değiştirir; dosyanın geri kalanı
bayt-bayt aynı kalır.

NE YAPMAZ:
  • `pid_map.json` dosyalarına DOKUNMAZ. Onlar "bu kaynak kaydı hangi pid
    olarak mint edildi" kaydıdır; oradaki eski pid YANLIŞ DEĞİL, TARİHTİR.
    Yeniden yazmak provenansı bozar. Gezinme sorunu ayrı bir katmanda
    (person_bridge, H60'ta üreticide onarıldı) çözülür.
  • Hedefi çözülemeyen pid'e dokunmaz — uydurma yönlendirme yapmaz.

Varsayılan KURU KOŞU. Uygulamak için --apply.
"""

import argparse
import json
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CANON = REPO / "data" / "canonical"

# Cerrahi kapsam: gezinmeye giren, üreticisi güvenle yeniden koşturulamayan
# yayın dosyaları. pid_map'ler BİLEREK dışarıda (yukarıdaki gerekçe).
HEDEFLER = [
    "web/public/books/visits.json",
    "web/public/books/visits_meta.json",
]

PID_RE = re.compile(r"iac:(person|place|work|event|institution|dynasty)-(\d+)")
_PROV = {}


def prov(kind: str, num: int) -> dict:
    k = (kind, num)
    if k not in _PROV:
        f = CANON / kind / f"iac_{kind}_{num:08d}.json"
        try:
            _PROV[k] = json.loads(f.read_text(encoding="utf-8")).get("provenance") or {}
        except (OSError, json.JSONDecodeError):
            _PROV[k] = {}
    return _PROV[k]


def kazanan(kind: str, num: int):
    """Zincir + döngü korumalı. Çözülemezse None (dokunulmaz)."""
    gorulen = set()
    while True:
        pr = prov(kind, num)
        if not pr:
            return None
        if not pr.get("deprecated"):
            return num
        m = PID_RE.match(str(pr.get("deprecated_in_favor_of") or ""))
        if not m or m.group(1) != kind:
            return None
        h = int(m.group(2))
        if h in gorulen:
            return None
        gorulen.add(num)
        num = h


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="değişikliği YAZ (varsayılan kuru koşu)")
    a = ap.parse_args()

    toplam_dosya = toplam_pid = toplam_gecis = 0
    for rel in HEDEFLER:
        p = REPO / rel
        if not p.is_file():
            print(f"atlandı (yok): {rel}")
            continue
        s = p.read_text(encoding="utf-8")
        esleme = {}
        for kind, num_s in set(PID_RE.findall(s)):
            num = int(num_s)
            if not prov(kind, num).get("deprecated"):
                continue
            kaz = kazanan(kind, num)
            if kaz is None or kaz == num:
                print(f"  ! çözülemedi, DOKUNULMADI: iac:{kind}-{num_s}")
                continue
            esleme[f"iac:{kind}-{num_s}"] = f"iac:{kind}-{kaz:08d}"
        if not esleme:
            print(f"temiz: {rel}")
            continue

        yeni = s
        for eski, yn in esleme.items():
            n = len(re.findall(re.escape(eski), yeni))
            toplam_gecis += n
            print(f"  {rel}: {eski} → {yn}  ({n} geçiş)")
            yeni = yeni.replace(eski, yn)
        toplam_dosya += 1
        toplam_pid += len(esleme)

        if a.apply:
            shutil.copy2(p, p.with_suffix(p.suffix + ".h60bak"))
            p.write_text(yeni, encoding="utf-8")

    kip = "UYGULANDI" if a.apply else "KURU KOŞU (yazılmadı)"
    print(f"\n{kip}: {toplam_dosya} dosya · {toplam_pid} ölü pid · {toplam_gecis} geçiş")
    if a.apply:
        print("  yedekler: *.h60bak (geri alma: dosyayı yedekten kopyala)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
