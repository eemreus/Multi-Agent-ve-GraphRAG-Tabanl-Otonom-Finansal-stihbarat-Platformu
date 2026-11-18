# Çalıştırma rehberi: RTX 4060'lı bilgisayarda (Hafta 3, #22)

Hedef: 157 sayfayı yerel modelle işleyip Neo4j'ye yazmak, 40 test sorusunu GraphRAG ile cevaplatmak, sonucu ölçmek. Komutlar Windows PowerShell içindir.

## 0. Bir kez kurulacaklar

1. **Git**, **Python 3.11 veya üstü** (kurarken "Add to PATH" işaretli olsun), **Docker Desktop**, **Ollama** (ollama.com).
2. Docker Desktop açık ve çalışır durumda olsun (sol altta yeşil).

## 1. Projeyi indir

```powershell
git clone https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu.git
cd Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONUTF8 = "1"
```

## 2. Ham veriyi yerleştir

Sıla'nın gönderdiği zip'i aç. İçindeki `THYAO`, `PGSUS`, `KCHOL`, `SAHOL` klasörlerini projedeki `data\ham\` klasörüne kopyala (var olan `.json` dosyalarının yanına `.txt` ve `.html` gelecek, üzerine yazılsın istersen evet de). Kontrol: `data\ham\THYAO\` içinde hem `.json` hem `.txt` görünmeli.

## 3. Neo4j ve model

```powershell
docker compose up -d
ollama pull llama3.1:8b
```

İlk komut Neo4j'yi başlatır (http://localhost:7474, kullanıcı `neo4j`, parola `paragoz-dev-sifre`). İkinci komut modeli indirir (yaklaşık 5 GB). RTX 4060'ın 8 GB belleği bu model için yeterli.

## 4. Önce küçük deneme

```powershell
python -m pytest -q
python -m src.graf.cli data\ornek\ornek1.txt --dry-run
```

Testler geçmeli. İkinci komut modelin örnek metinden varlık ve ilişki çıkarmasını ekrana yazar. Çıktı bozuksa ya da boşsa dur, çıktıyı bana yapıştır.

## 5. Asıl çalıştırma

```powershell
python -m src.graf.ingest --test-seti --limit 3        # 3 sayfa dene
python -m src.graf.ingest --test-seti                  # dondurulmuş 40 sayfa
python -m src.graphrag.degerlendir --limit 3           # 3 soru dene
python -m src.graphrag.degerlendir                     # 40 soru -> results\graphrag.json
```

Çıkarımlar `data\cikarim\` içinde önbelleğe alınır, komut yarıda kesilirse tekrar çalıştırınca kaldığı yerden devam eder. Grafı görmek için Neo4j Browser'da: `MATCH (a)-[r]->(b) RETURN a,r,b LIMIT 50`

## 6. Ölçüm

Sıla vektör RAG sonucunu (`results\vektor.json`) hazırlayınca:

```powershell
python -m src.olcum.run results\graphrag.json results\vektor.json
```

Çıkan tablo `docs/11-hafta3-olcum.md` içine yazılır.

## Sorun çıkarsa

- `Connection refused` (7687): Docker Desktop açık mı, `docker compose up -d` çalıştı mı?
- `Connection refused` (11434): Ollama uygulaması açık mı?
- Model çok yavaşsa: `ollama ps` ile GPU kullanıp kullanmadığına bak (PROCESSOR sütunu `100% GPU` olmalı).
- Her hatada ekran görüntüsü ya da yazıyı bana yapıştırman yeter.
