"""Soru-cevap önbelleği: aynı soru tekrar gelirse modele gitmeden cevap döner.

İki gerçekleme aynı arayüzü sunar (get/set): Redis (üretim) ve bellek (test ve Redis yokken).
Redis erişilemezse önbellek sessizce devre dışı kalır; istek her zaman modele düşer.
Yalnızca başarılı cevaplar saklanır, hatalar saklanmaz.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from typing import Callable

log = logging.getLogger(__name__)


def onbellek_anahtari(soru: str, surum: str = "v1") -> str:
    """Boşluk ve büyük/küçük harf farkını yok sayar. `surum` model ya da istem değişince eski cevapları eler."""
    norm = " ".join(soru.split()).casefold()
    return hashlib.sha256(f"{surum}|{norm}".encode("utf-8")).hexdigest()


class BellekOnbellek:
    def __init__(self, ttl_sn: float = 3600, maks: int = 256, saat: Callable[[], float] = time.monotonic):
        self.ttl, self.maks, self.saat = ttl_sn, maks, saat
        self._veri: dict[str, tuple[float, dict]] = {}
        self._kilit = threading.Lock()

    def get(self, anahtar: str) -> dict | None:
        with self._kilit:
            kayit = self._veri.get(anahtar)
            if kayit is None:
                return None
            bitis, deger = kayit
            if self.saat() >= bitis:
                del self._veri[anahtar]
                return None
            return json.loads(json.dumps(deger))  # kopya: çağıran sonucu değiştirse bile önbellek bozulmaz

    def set(self, anahtar: str, deger: dict) -> None:
        with self._kilit:
            if len(self._veri) >= self.maks and anahtar not in self._veri:
                self._veri.pop(min(self._veri, key=lambda k: self._veri[k][0]))  # en eski kaydı at
            self._veri[anahtar] = (self.saat() + self.ttl, json.loads(json.dumps(deger)))


class RedisOnbellek:
    """istemci: redis.Redis benzeri (get, set(ex=...)). Her hata yutulur ve loglanır."""

    def __init__(self, istemci, ttl_sn: int = 3600, onek: str = "paragoz:sor:"):
        self.istemci, self.ttl, self.onek = istemci, int(ttl_sn), onek

    def get(self, anahtar: str) -> dict | None:
        try:
            ham = self.istemci.get(self.onek + anahtar)
            return json.loads(ham) if ham else None
        except Exception as e:
            log.warning("Redis okunamadı, modele düşülüyor: %s", type(e).__name__)
            return None

    def set(self, anahtar: str, deger: dict) -> None:
        try:
            self.istemci.set(self.onek + anahtar, json.dumps(deger, ensure_ascii=False), ex=self.ttl)
        except Exception as e:
            log.warning("Redis yazılamadı: %s", type(e).__name__)


def ortamdan() -> RedisOnbellek | None:
    """REDIS_URL tanımlıysa Redis önbelleği; yoksa önbellek kapalı. REDIS_TTL_SN (varsayılan 3600)."""
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    import redis
    istemci = redis.Redis.from_url(url, decode_responses=True, socket_timeout=0.5, socket_connect_timeout=0.5)
    return RedisOnbellek(istemci, ttl_sn=int(os.getenv("REDIS_TTL_SN", "3600")))
