"""Veri toplama hatti: SearXNG ile ara, sayfayi cek, metni cikar, dondurulmus kopya olarak sakla."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
import trafilatura

SEARXNG_URL = "http://localhost:8888/search"
HAM_KLASOR = Path("data/ham")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
MIN_METIN = 500                      # bundan kisa metin "bos sayfa" sayilir
BOT_KODLARI = {403, 429, 503}
BOT_IZLERI = (b"anubis", b"just a moment", b"cf-browser-verification", b"checking your browser")
IZLEME_PARAMETRELERI = ("utm_", "srsltid", "fbclid", "gclid")
HARIC_DESENLER = ("kap.org.tr/tr/sirket-bilgileri", "eksisozluk.com", "%e2%80", "%ef%bf%bd", "iletisim", "cagri-merkezi", "traveland.com.tr", "://x.com", "://facebook.com", "://twitter.com", "://instagram.com", "://youtube.com", "://prezi.com", "://yandex.com.tr", "tradingview.com", "sirketortagim.com", "mea-ilk-airbus", "esas.com.tr/tr/hakkimizda")   # sabit profil sayfalari, iliski/olay icermez
MAKS_ALAN_ADI = 6                    # bir siteden sirket basina en fazla sayfa

from .sorgular import SIRKETLER


def normalize_url(url):
    """www. onekini, takip parametrelerini, #parcayi ve sondaki / isaretini atar."""
    p = urlparse(url)
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    q = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith(IZLEME_PARAMETRELERI)]
    yol = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme.lower(), host, yol, "", urlencode(q), ""))


def alan_adi(url):
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def ara(sorgu, adet=10):
    r = requests.get(SEARXNG_URL, params={"q": sorgu, "format": "json", "language": "tr"}, timeout=30)
    r.raise_for_status()
    return [{"url": s["url"], "baslik": s.get("title", "")} for s in r.json().get("results", []) if urlparse(s["url"]).scheme in ("http", "https") and urlparse(s["url"]).netloc][:adet]


def cek(url):
    """Donus: (durum, ham_icerik). durum: ok | bot_engeli | zaman_asimi | bulunamadi | hata"""
    for deneme in range(2):
        try:
            r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9"}, timeout=15)
        except requests.Timeout:
            if deneme == 0:
                continue
            return "zaman_asimi", None
        except requests.RequestException as e:
            print(f"    [hata] {url[:70]} -> {type(e).__name__}")
            return "hata", None
        if r.status_code in BOT_KODLARI:
            return "bot_engeli", None
        if r.status_code in (404, 410):
            return "bulunamadi", None
        if r.status_code >= 400:
            print(f"    [hata] {url[:70]} -> HTTP {r.status_code}")
            return "hata", None
        tur = r.headers.get("Content-Type", "").lower()
        if "html" not in tur and "xml" not in tur:
            return "desteklenmeyen", None
        govde = r.content
        if len(govde) < 100000 and any(i in govde.lower() for i in BOT_IZLERI):
            return "bot_engeli", None
        return "ok", govde
    return "zaman_asimi", None


def _mevcut(klasor):
    """Daha once kaydedilmis sayfalarin URL, icerik ozeti ve site sayaclarini okur (tekrar calistirilabilsin diye)."""
    urller, ozetler, alanlar = set(), set(), {}
    for j in klasor.glob("*.json"):
        try:
            k = json.loads(j.read_text(encoding="utf-8"))
        except ValueError:
            continue
        n = normalize_url(k["url"])
        urller.add(n)
        if k.get("metin_sha256"):
            ozetler.add(k["metin_sha256"])
        a = alan_adi(n)
        alanlar[a] = alanlar.get(a, 0) + 1
    return urller, ozetler, alanlar


def kaydet(kod, sorgu, url, orijinal_url, baslik, ham, metin_ozetleri):
    """Donus: ('ok', id) | ('bos', None) | ('ayni_icerik', None)"""
    klasor = HAM_KLASOR / kod
    metin = trafilatura.extract(ham, url=url, include_comments=False, favor_precision=True)
    if not metin or len(metin) < MIN_METIN:
        return "bos", None
    metin_ozeti = hashlib.sha256(metin.encode("utf-8")).hexdigest()
    if metin_ozeti in metin_ozetleri:
        return "ayni_icerik", None
    metin_ozetleri.add(metin_ozeti)
    ozet = hashlib.sha256(ham).hexdigest()
    sid = ozet[:12]
    (klasor / f"{sid}.html").write_bytes(ham)
    (klasor / f"{sid}.txt").write_text(metin, encoding="utf-8")
    kunye = {
        "id": sid, "sirket": kod, "url": url, "orijinal_url": orijinal_url, "alan_adi": alan_adi(url),
        "baslik": baslik, "sorgu": sorgu,
        "erisim_tarihi": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": ozet, "metin_sha256": metin_ozeti, "metin_uzunlugu": len(metin),
    }
    (klasor / f"{sid}.json").write_text(json.dumps(kunye, ensure_ascii=False, indent=2), encoding="utf-8")
    return "ok", sid


def topla(kod, hedef=40, bekleme=1.0):
    sayac = {"ok": 0, "bos": 0, "ayni_icerik": 0, "bot_engeli": 0, "zaman_asimi": 0,
             "bulunamadi": 0, "hata": 0, "desteklenmeyen": 0, "tekrar": 0, "haric": 0, "alan_limiti": 0}
    klasor = HAM_KLASOR / kod
    klasor.mkdir(parents=True, exist_ok=True)
    gorulen, metin_ozetleri, alanlar = _mevcut(klasor)
    kayitli = len(gorulen)
    _global_yukle(gorulen, metin_ozetleri)
    for sorgu in SIRKETLER[kod]:
        if kayitli >= hedef:
            break
        try:
            sonuclar = ara(sorgu)
        except requests.RequestException as e:
            print(f"  [arama hatasi] {sorgu}: {e}")
            continue
        for s in sonuclar:
            if kayitli >= hedef:
                break
            n = normalize_url(s["url"])
            if any(d in n.lower() for d in HARIC_DESENLER) or urlparse(n).path == "/":
                sayac["haric"] += 1
                continue
            if n in gorulen:
                sayac["tekrar"] += 1
                continue
            a = alan_adi(n)
            if alanlar.get(a, 0) >= MAKS_ALAN_ADI:
                sayac["alan_limiti"] += 1
                continue
            gorulen.add(n)
            durum, ham = cek(n)
            if durum != "ok":
                sayac[durum] += 1
                continue
            sonuc, sid = kaydet(kod, sorgu, n, s["url"], s["baslik"], ham, metin_ozetleri)
            if sonuc != "ok":
                sayac[sonuc] += 1
            else:
                sayac["ok"] += 1
                kayitli += 1
                alanlar[a] = alanlar.get(a, 0) + 1
                print(f"  [ok {kayitli}/{hedef}] {n[:90]}")
            time.sleep(bekleme)
    return sayac, kayitli


def _global_yukle(gorulen, metin_ozetleri):
    """Tum sirket klasorlerindeki sayfalari ve kara listeyi 'goruldu' sayar (sirketler arasi tekrari onler)."""
    for j in HAM_KLASOR.glob("*/*.json"):
        try:
            k = json.loads(j.read_text(encoding="utf-8"))
        except ValueError:
            continue
        gorulen.add(normalize_url(k["url"]))
        if k.get("metin_sha256"):
            metin_ozetleri.add(k["metin_sha256"])
    kl = HAM_KLASOR / "_kara_liste.txt"
    if kl.exists():
        for satir in kl.read_text(encoding="utf-8-sig").splitlines():
            if satir.strip():
                gorulen.add(normalize_url(satir.strip()))