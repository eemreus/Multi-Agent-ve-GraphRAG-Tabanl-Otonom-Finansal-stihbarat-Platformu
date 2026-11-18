# Hafta 3 Ölçüm Düzeni (H3-7, #24)

Ölçüm kodu hazır; gerçek sayılar GraphRAG (#22) ve vektör RAG (#23) baseline'ları, dondurulmuş test seti (#19) ile çalışınca bu dosyaya yazılacak.

## Metrikler

| Metrik | Nasıl hesaplanır | Hedef |
|--------|------------------|-------|
| Yanıt doğruluğu (F1) | Kelime düzeyinde F1 (Türkçe karakterler ve şirket ekleri normalleştirilir), 40 soru ortalaması. Kazanç = (GraphRAG − vektör) / vektör | ≥ +%20 |
| Uydurma atıf oranı | Cevaptaki her atıf için: kaynak kaydı var mı ve alıntı o kaynağın metninde geçiyor mu. Geçmeyen atıf uydurma sayılır | < %5 |
| p@95 gecikme | Soru başına uçtan uca süre (ms), en yakın sıra yüzdeliği | < 2500 ms |

## Kullanım

```bash
python -m src.olcum.run results/sonuc.json
```

Girdi biçimi `src/olcum/run.py` içinde belgeli. `results/ornek-sonuc.json` yalnızca biçimi göstermek için uydurulmuş tek satırlık örnektir, gerçek sonuç değildir.

## Sonuç tablosu

| Metrik | Ölçülen | Hedef | Durum |
|---|---|---|---|
| F1 kazancı | henüz ölçülmedi | ≥ +%20 | bekliyor |
| Uydurma atıf oranı | henüz ölçülmedi | < %5 | bekliyor |
| p@95 gecikme | henüz ölçülmedi | < 2500 ms | bekliyor |
