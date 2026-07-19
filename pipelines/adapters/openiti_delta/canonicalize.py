"""
canonicalize.py — openiti_works canonicalize'ının aynısı (import); ayrı
adapter olmasının TEK nedeni: ana adapter'ı 9,104 kayıt üzerinde yeniden
koşturmak H13 S-B başlık zenginleştirmelerini EZERDİ (run_adapter preserve
listesi label'ları kapsamaz). Delta girdisi yalnız 73 yeni kitap.
"""
from pipelines.adapters.openiti_works.canonicalize import canonicalize  # noqa: F401
