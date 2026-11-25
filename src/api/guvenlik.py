"""API anahtarı doğrulama ve istek sınırı (REQ-05). Saf Python, FastAPI gerektirmez."""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from collections import defaultdict, deque
from typing import Callable


def _ozet(anahtar: str) -> str:
    return hashlib.sha256(anahtar.encode("utf-8")).hexdigest()


class ApiAnahtarlari:
    """İzinli anahtarların SHA-256 özetlerini tutar; düz metin anahtar bellekte saklanmaz."""

    def __init__(self, anahtarlar: list[str]):
        self._ozetler = {_ozet(a) for a in anahtarlar if a}

    @classmethod
    def ortamdan(cls, ad: str = "API_KEYS") -> "ApiAnahtarlari":
        """API_KEYS=anahtar1,anahtar2 (virgülle ayrılmış)."""
        return cls([a.strip() for a in os.environ.get(ad, "").split(",") if a.strip()])

    def gecerli(self, anahtar: str | None) -> bool:
        if not anahtar or not self._ozetler:
            return False
        o = _ozet(anahtar)
        return any(hmac.compare_digest(o, x) for x in self._ozetler)


class HizSiniri:
    """Anahtar başına kayan pencere sınırı: pencere_sn saniyede en fazla maks istek."""

    def __init__(self, maks: int = 30, pencere_sn: float = 60.0, saat: Callable[[], float] = time.monotonic):
        self.maks, self.pencere, self.saat = maks, pencere_sn, saat
        self._kayit: dict[str, deque] = defaultdict(deque)

    def izin(self, anahtar: str) -> tuple[bool, float]:
        """(izinli_mi, beklenecek_saniye). İzinliyse isteği sayar."""
        simdi = self.saat()
        k = self._kayit[_ozet(anahtar)]
        while k and simdi - k[0] >= self.pencere:
            k.popleft()
        if len(k) >= self.maks:
            return False, max(0.0, self.pencere - (simdi - k[0]))
        k.append(simdi)
        return True, 0.0
