"""GraphRAG baseline: soru -> varlık bağlama -> graf komşuluğu (≤2 adım) -> kanıtlı cevap.

Her adım ölçülür; cevaptaki her atıf yalnızca grafın döndürdüğü kanıt cümlelerinden seçilebilir
(uydurma atıf oranını düşük tutmak için doğrulanır)."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Callable

from src.graf.schema import normalize_name

SORU_VARLIK_PROMPT = """Aşağıdaki Türkçe sorudaki şirket, kişi ve kuruluş adlarını çıkar.
SADECE JSON döndür: {{"varliklar": ["ad1", "ad2"]}}
SORU: {soru}"""

CEVAP_PROMPT = """Sen finansal bir araştırma asistanısın. YALNIZCA aşağıdaki bilgilere dayanarak soruyu kısa cevapla.
Önce PASAJLARA bak (kaynak metinden alıntılar), GRAF İLİŞKİLERİ varlıklar arası bağlantıyı gösterir.
Cevap için gereken bilgi birden fazla yerde olabilir, bunları birleştir. Bilgi gerçekten yoksa cevabı "Kanıt yok" yaz.
Cevap kısa olsun (bir iki cümle), rakam ve adları metindeki gibi yaz.
Atıf için dayandığın cümleyi AYNEN kopyala ve köşeli parantezdeki kaynak numarasını yaz.
SADECE JSON döndür: {{"cevap": "...", "atiflar": [{{"source_id": "...", "quote": "..."}}]}}

SORU: {soru}

PASAJLAR:
{pasajlar}

GRAF İLİŞKİLERİ:
{kanitlar}"""

KOMSU_1 = ("MATCH (a {id: $id})-[r]-(b) RETURN a.name AS a, type(r) AS rel, startNode(r).name AS bas, "
           "endNode(r).name AS son, r.evidence AS evidence, r.source_ids AS source_ids, r.confidence AS conf "
           "ORDER BY r.confidence DESC LIMIT 40")
KOMSU_2 = ("MATCH (a {id: $id})-[]-(b)-[r]-(c) WHERE c.id <> a.id RETURN b.name AS a, type(r) AS rel, "
           "startNode(r).name AS bas, endNode(r).name AS son, r.evidence AS evidence, r.source_ids AS source_ids, "
           "r.confidence AS conf ORDER BY r.confidence DESC LIMIT 60")
SAYFA_TOHUM = "MATCH (a {id: $id}) UNWIND coalesce(a.source_ids, []) AS sid RETURN sid, 10 AS w"
MIN_DERINLIK, MAKS_DERINLIK, VARSAYILAN_DERINLIK = 1, 3, 2


def derinlik_sinirla(derinlik) -> int:
    """Graf geçiş derinliğini 1-3 arasına sıkıştırır (REQ-05: multi-hop derinlik sınırı).
    Cypher'da değişken uzunluklu örüntü parametreyle verilemez, bu yüzden sorguya sayı olarak yazılır;
    tamsayıya çevirip sınırlamak hem enjeksiyonu hem pahalı sorguları engeller."""
    try:
        d = int(derinlik)
    except (TypeError, ValueError):
        return VARSAYILAN_DERINLIK
    return max(MIN_DERINLIK, min(MAKS_DERINLIK, d))


def sayfa_komsu_sorgusu(derinlik: int = VARSAYILAN_DERINLIK) -> str:
    d = derinlik_sinirla(derinlik)
    return (f"MATCH (a {{id: $id}})-[*1..{d}]-(b) WITH DISTINCT b UNWIND coalesce(b.source_ids, []) AS sid "
            "RETURN sid, count(*) AS w ORDER BY w DESC LIMIT 20")


SAYFA_KOMSU = sayfa_komsu_sorgusu(VARSAYILAN_DERINLIK)
BAGLA = ("MATCH (n) WHERE (n:Company OR n:Person OR n:Event OR n:Location) AND n.normalized_name IS NOT NULL "
         "AND (n.normalized_name = $norm OR n.normalized_name CONTAINS $norm OR ($norm CONTAINS n.normalized_name "
         "AND size(n.normalized_name) > 4)) RETURN n.id AS id, n.name AS name LIMIT 5")


@dataclass
class Sonuc:
    cevap: str
    atiflar: list[dict] = field(default_factory=list)
    gecikme_ms: float = 0.0
    kanit_sayisi: int = 0
    gorunen_varliklar: list[str] = field(default_factory=list)
    atilan_atif: int = 0
    tokens_in: int = 0
    tokens_out: int = 0


def _json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        return json.loads(m.group(0)) if m else {}


def kanit_topla(query: Callable, soru: str, generate: Callable[[str], str], maks: int = 40) -> tuple[list[dict], list[str], list[str]]:
    try:
        adlar = _json(generate(SORU_VARLIK_PROMPT.format(soru=soru))).get("varliklar", [])
    except Exception:
        adlar = []
    # model hiçbir şey vermezse soru metninden büyük harfle başlayan sözcükler denenir
    adlar = adlar or re.findall(r"\b[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ.]+(?:\s+[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ.]+)*", soru)
    ids, adlar_bulunan = [], []
    for ad in adlar:
        norm = normalize_name(str(ad))
        if len(norm) < 3:
            continue
        for r in query(BAGLA, {"norm": norm}):
            if r["id"] not in ids:
                ids.append(r["id"]); adlar_bulunan.append(r["name"])
    satirlar, goruldu = [], set()
    for i in ids:
        for q in (KOMSU_1, KOMSU_2):
            for r in query(q, {"id": i}):
                anahtar = (r["bas"], r["rel"], r["son"], r["evidence"])
                if r.get("evidence") and anahtar not in goruldu:
                    goruldu.add(anahtar); satirlar.append(r)
    satirlar.sort(key=lambda r: -(r.get("conf") or 0))
    return satirlar[:maks], adlar_bulunan, ids


def kanit_metni(satirlar: list[dict]) -> str:
    out = []
    for r in satirlar:
        kaynak = (r.get("source_ids") or ["?"])[0]
        out.append(f"[{kaynak}] ({r['bas']} -{r['rel']}-> {r['son']}) {r['evidence']}")
    return "\n".join(out)


_DURAK = {"kac", "kaç", "hangi", "nedir", "midir", "olarak", "icin", "için", "bir", "kim", "kimdir", "nasil", "ne",
          "ile", "ve", "veya", "olan", "oldugu", "ise", "da", "de", "mi", "mu", "ait", "gore", "göre", "sonra", "once"}


def _kok(sozcuk: str) -> str:
    return normalize_name(sozcuk)[:5]  # Türkçe ekler için kaba gövde: ilk 5 harf


def _anahtarlar(metin: str) -> set[str]:
    return {_kok(w) for w in re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", metin) if len(w) > 2 and w.lower() not in _DURAK}


def _ws(x: str) -> str:
    return re.sub(r"\s+", " ", x.replace("’", "'")).strip().lower()


def _duz_harita(x: str) -> tuple[str, list[int]]:
    """Atıf karşılaştırması için normalleştirir (küçük harf, noktalama ve tırnak farkı yok sayılır).
    Her normalleştirilmiş harfin özgün metindeki konumunu da döndürür."""
    cikti, harita, bosluk = [], [], True
    for i, c in enumerate(x):
        c = "i" if c == "İ" else "ı" if c == "I" else c.lower()[0]
        if c.isalnum() or c == "_":
            cikti.append(c); harita.append(i); bosluk = False
        elif not bosluk:
            cikti.append(" "); harita.append(i); bosluk = True
    while cikti and cikti[-1] == " ":
        cikti.pop(); harita.pop()
    return "".join(cikti), harita


def _duz(x: str) -> str:
    return _duz_harita(x)[0]


def alinti_bul(alinti: str, sayfa: str | None) -> str | None:
    """Alıntı sayfada geçiyorsa sayfadaki BİREBİR metni döndürür, yoksa None.
    Model alıntıyı küçük harfle, noktalamasız ya da "..." ile kesik yazabilir; kabul ederiz ama cevaba modelin
    yazdığı değil kaynağın kendi metni girer, böylece atıf her zaman kaynakta aynen bulunur.
    "..." ile kesilmiş alıntıda her parça (en az 8 harf) sayfada olmalı; en uzun parçanın metni döner."""
    if not sayfa:
        return None
    duz_sayfa, harita = _duz_harita(sayfa)
    parcalar = [_duz(p) for p in re.split(r"\.{2,}|…", alinti)]
    parcalar = [p for p in parcalar if p]
    if not parcalar or any(len(p) < 8 or p not in duz_sayfa for p in parcalar):
        return None
    en_uzun = max(parcalar, key=len)
    bas = duz_sayfa.index(en_uzun)
    return sayfa[harita[bas]:harita[bas + len(en_uzun) - 1] + 1]


def alinti_sayfada_mi(alinti: str, sayfa: str | None) -> bool:
    return alinti_bul(alinti, sayfa) is not None


def iliski_sirala(satirlar: list[dict], soru: str, n: int = 10) -> list[dict]:
    q = _anahtarlar(soru)
    skor = lambda r: (len(q & _anahtarlar(f"{r['bas']} {r['son']} {r['evidence']}")), r.get("conf") or 0)
    return sorted(satirlar, key=skor, reverse=True)[:n]


def sayfa_adaylari(query: Callable, ids: list[str], maks: int = 16, derinlik: int = VARSAYILAN_DERINLIK) -> list[str]:
    """Bağlanan varlıkların kendi sayfaları (ağırlık 10) ve komşularının sayfaları (derinlik 1-3, varsayılan 2)."""
    agirlik: dict[str, float] = {}
    komsu = sayfa_komsu_sorgusu(derinlik)
    for i in ids:
        for q in (SAYFA_TOHUM, komsu):
            for r in query(q, {"id": i}):
                if r.get("sid"):
                    agirlik[r["sid"]] = agirlik.get(r["sid"], 0) + float(r.get("w") or 1)
    return [k for k, _ in sorted(agirlik.items(), key=lambda kv: -kv[1])][:maks]


def pasaj_sec(soru: str, sayfalar: list[str], sayfa_metni: Callable[[str], str | None], n: int = 6, boy: int = 1200):
    """Aday sayfaları parçalar, soruyla en çok örtüşen n parçayı seçer (nadir sözcükler daha değerli)."""
    q = _anahtarlar(soru)
    parcalar = []
    for sid in sayfalar:
        t = sayfa_metni(sid)
        if not t:
            continue
        for i in range(0, len(t), boy - 200):
            parcalar.append((sid, t[i:i + boy]))
    if not parcalar:
        return []
    kume = [_anahtarlar(p[1]) for p in parcalar]
    df = {k: sum(1 for c in kume if k in c) for k in q}
    skor = [sum(1 / (1 + df[k]) for k in q if k in c) for c in kume]
    sirali = sorted(range(len(parcalar)), key=lambda i: -skor[i])[:n]
    return [parcalar[i] for i in sirali if skor[i] > 0]


def cevapla(query: Callable, soru: str, generate: Callable[[str], str],
            sayfa_metni: Callable[[str], str | None] | None = None) -> Sonuc:
    t0 = time.perf_counter()
    satirlar, adlar, ids = kanit_topla(query, soru, generate)
    satirlar = iliski_sirala(satirlar, soru)
    pasajlar = pasaj_sec(soru, sayfa_adaylari(query, ids), sayfa_metni) if (sayfa_metni and ids) else []
    if not satirlar and not pasajlar:
        return Sonuc("Kanıt yok", [], (time.perf_counter() - t0) * 1000, 0, adlar)
    pasaj_metni = "\n\n".join(f"[{sid}] {t}" for sid, t in pasajlar) or "(yok)"
    try:
        j = _json(generate(CEVAP_PROMPT.format(soru=soru, pasajlar=pasaj_metni, kanitlar=kanit_metni(satirlar) or "(yok)")))
    except Exception:
        j = {}
    izinli = {(sid, r["evidence"].strip()) for r in satirlar for sid in (r.get("source_ids") or [])}
    sayfalar_metin = {sid: _ws(t) for sid, t in pasajlar}
    atiflar, atilan = [], 0
    for a in j.get("atiflar", []) or []:
        sid, q = str(a.get("source_id", "")), str(a.get("quote", "")).strip()
        if (sid, q) in izinli:
            atiflar.append({"source_id": sid, "quote": q})
            continue
        # Model bazen doğru alıntıyı yanlış sayfa numarasıyla verir: önce söylediği sayfaya, sonra
        # modele verilen diğer sayfalara bakılır. Alıntı hiçbirinde yoksa uydurma sayılır.
        adaylar = [sid] + [x for x in sayfalar_metin if x != sid]
        bulunan = None
        for x in adaylar:
            metin = alinti_bul(q, sayfa_metni(x)) if sayfa_metni else None
            if metin:
                bulunan = (x, metin)
                break
        if bulunan:
            atiflar.append({"source_id": bulunan[0], "quote": bulunan[1]})  # kaynağın birebir metni
        else:
            atilan += 1  # kaynakta bulunamayan atıf: uydurma sayılır ve cevaba girmez
    return Sonuc(str(j.get("cevap", "Kanıt yok")), atiflar, (time.perf_counter() - t0) * 1000,
                 len(satirlar) + len(pasajlar), adlar, atilan)
