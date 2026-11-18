# Bilgi çıkarım ajanı (Hafta 3, issue #21)

Metin → yerel model (Ollama) → şema doğrulama → Neo4j. Şema: [docs/06-neo4j-graf-semasi.md](../docs/06-neo4j-graf-semasi.md), akış: [docs/flow-varlik-iliski-cikarimi.md](../docs/flow-varlik-iliski-cikarimi.md).

## Kendi bilgisayarında çalıştırma

```bash
pip install -r requirements.txt
cp .env.example .env            # parolayı istersen değiştir
docker compose up -d            # Neo4j: http://localhost:7474
ollama pull llama3.1:8b         # RTX 3060 için; VRAM yetmezse llama3.2:3b dene
python -m src.graf.cli data/ornek/ornek1.txt --dry-run          # sadece çıkarım, yazmaz
python -m src.graf.cli data/ornek/ornek1.txt --source-id 1 --init-schema   # Neo4j'ye yazar
```

Neo4j Browser'da kontrol: `MATCH (a)-[r]->(b) RETURN a,r,b LIMIT 50`

## Testler (model/DB gerekmez)

```bash
python -m pytest -q
```

## Hata yönetimi

- Geçersiz JSON/şema: en fazla 2 yeniden deneme, olmazsa parça atlanır ve loglanır (API modele yükseltme Hafta 4+).
- Kanıt cümlesi metinde bulunmayan ilişki atılır (uydurma atıf riskine karşı).
- Neo4j yazma hatası: 3 deneme, üssel bekleme; sonra istisna (Redis hata kuyruğu sonraki hafta).
- Aynı ilişki tekrar gelirse `MERGE` ile kopya oluşmaz, `source_ids` genişler.
