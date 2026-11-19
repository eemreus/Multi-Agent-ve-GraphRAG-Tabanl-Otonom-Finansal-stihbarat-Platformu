# Hafta 3 demo akışı (#26, 5 dakika)

Slaytlar: `docs/sunum/ParaGoz-Hafta3-Demo.pptx` ve `.pdf` (10 slayt; son slayt yedek). Konuşma notları PPTX'in not bölümünde.

## Önceden hazırlık (demodan en az 15 dakika önce, Sıla'nın RTX 4060'lı bilgisayarında)

1. Docker Desktop açık, Ollama uygulaması açık olsun.
2. `docker compose up -d`, sonra tarayıcıda http://localhost:7474 (kullanıcı `neo4j`, parola `paragoz-dev-sifre`). Graf dolu olmalı: `MATCH (n) RETURN labels(n)[0] AS tur, count(*) AS adet` sorgusu 5 tür göstermeli.
3. Terminalde proje klasöründe sanal ortamı etkinleştir (`.venv\Scripts\Activate.ps1`) ve `$env:PYTHONUTF8 = "1"` yaz.
4. **Isınma:** demo sorusunu bir kez çalıştır (aşağıda). İlk çağrı modeli belleğe yükler ve yavaştır; sınıfta ikinci çağrı daha hızlı olur.
5. Terminal yazı boyutunu büyüt, ikinci ekran/sunum yanında hazır dursun.

## Dakika dakika

| Süre | Ne gösterilir | Kim | Ne söylenir |
|---|---|---|---|
| 0:00–0:30 | Slayt 1–2 | Emre | Projeyi ve üç hedefi (F1 +%20, uydurma atıf <%5, p95 <2,5 sn) söyle |
| 0:30–1:15 | Slayt 3–4 | Sıla | Sistem akışı ve dondurulmuş test seti (40 sayfa, 40 soru) |
| 1:15–2:00 | Slayt 5–6 | Emre | 0,035 → 0,443; vektör RAG 0,509; üç hedeften biri karşılandı. Dürüstçe söyle |
| 2:00–3:30 | **Canlı demo** (slayt 9) | Sıla yazar, Emre anlatır | Aşağıdaki iki soru |
| 3:30–4:15 | Slayt 7 | Emre | Bulgu: graf bir dizin olarak işe yarıyor, doğru sayfaya ulaşmak darboğaz |
| 4:15–5:00 | Slayt 8 | Sıla | Hafta 4 planı; sorulara hazır ol (slayt 10 yedek) |

## Canlı demo adımları

**Adım 1: Graf (yaklaşık 30 sn).** Neo4j Browser'da:

```cypher
MATCH (a)-[r]->(b) RETURN a,r,b LIMIT 50
```

Söyle: "Düğümler şirket, kişi, olay; her kenarın kaynak sayfası ve kanıt cümlesi var."

**Adım 2: Soru 1, iki adım (yaklaşık 30 sn bekleme).**

```powershell
python -m src.graphrag.sor --no K10
```

Soru: *Sabancı Holding Stratejik Yatırımlar Başkanı Murat Pınar daha önce hangi şirketin CEO'suydu ve bu şirketin faaliyet sektörü hangisidir?* Beklenen cevap: Enerjisa Enerji; enerji. Bu soruda GraphRAG vektör RAG'den iyi çıktı (F1 0,60 ve 0,36) ve atıfta doğru sayfa var.

**Adım 3: Soru 2, tek adım.**

```powershell
python -m src.graphrag.sor --no S03
```

Soru: *THY'nin Air Europa'ya dönüştürülebilir borç olarak yatıracağı tutar nedir?* Beklenen cevap: 300 milyon Euro (355 milyon dolar). Ölçümde bu soru GraphRAG'de 0,67, vektör RAG'de 1,0 aldı; kısmi puan beklenir, dürüstçe söyle.

**Adım 4: Atıfı göster.** Çıktıdaki ATIFLAR bölümünde alıntının kaynak sayfa künyesini göster ve "atıf sayfa metninde doğrulanıyor, bu yüzden uydurma atıf %0" de.

## Yedek planlar

- **Model cevap vermezse ya da çok yavaşsa** (soru başına 15–30 sn normaldir, ilk çağrı daha uzun): beklerken Adım 1'i anlat. 60 sn'yi geçerse durdur (Ctrl+C) ve `results/puanlar.csv` dosyasını aç: soru bazında puanları göster.
- **Neo4j açılmazsa:** `docs/06-neo4j-graf-semasi.md` ve slayt 3'ü göster, canlı demo yapılamadığını söyle.
- **Sunum bilgisayarı başka ise:** demo yalnızca Sıla'nın bilgisayarında çalışır (GPU, Docker, Ollama orada). Ekranı paylaşmak ya da onun bilgisayarından sunmak gerekir.

## Beklenen sorular

- *Neden vektör RAG önde?* Sorular çoğunlukla rakam/tarih/tutar istiyor; bunlar grafa ilişki olarak girmiyor. Graf burada yalnızca hangi sayfalara bakılacağını belirliyor ve doğru sayfa atıflarda 14/40 soruda görünüyor. Hafta 4'te iki yöntemi birleştireceğiz.
- *Gecikme neden 27 sn?* Soru başına iki model çağrısı, yerel 8B model. Hedef bu kurulumla gerçekçi değildi; Hafta 4'te çağrı sayısını azaltmayı deneyeceğiz.
- *Test seti neden küçük?* 40 sayfa, 40 soru; Hafta 3 için baseline. Sonuçlar bu boyutta kaba ölçümdür.
