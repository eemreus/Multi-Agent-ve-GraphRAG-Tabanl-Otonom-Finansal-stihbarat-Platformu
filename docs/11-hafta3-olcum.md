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

## Çalıştırma günlüğü (GraphRAG, 40 soru, F1 vektör RAG = 0,509)

| Tur | Değişiklik | GraphRAG F1 | Not |
|---|---|---|---|
| 1 | Yalnızca graftaki ilişki cümleleri modele verildi | 0,035 | Soruların çoğu rakam/tarih/tutar soruyor, bunlar ilişki olarak grafa girmiyor; model "Kanıt yok" dedi |
| 2 | Graf, varlıkların sayfalarını bulur; sayfalardan soruyla örtüşen 6 parça modele verilir | 0,315 | Türlere göre: tek 0,531, iki 0,304, üç 0,206, çelişki 0,137. Atıfı doğru sayfayı içeren soru 12/40: aday sayfa seçimi sınırlıydı (6 sayfa) |
| 3 | Aday sayfa sınırı 6 → 16 | (ölçülecek) | |

## Sonuç tablosu

| Metrik | Ölçülen | Hedef | Durum |
|---|---|---|---|
| F1 kazancı | henüz ölçülmedi | ≥ +%20 | bekliyor |
| Uydurma atıf oranı | henüz ölçülmedi | < %5 | bekliyor |
| p@95 gecikme | henüz ölçülmedi | < 2500 ms | bekliyor |
