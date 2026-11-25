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
| 3 | Aday sayfa sınırı 6 → 16 | **0,443** | Türlere göre: tek 0,824, iki 0,461, üç 0,196, çelişki 0,123. "Kanıt yok" diyen 5 soru, doğru sayfa atıfta 14/40 |

## Sonuç tablosu (3. tur, 40 soru, 159 sayfalık havuz)

| Metrik | Ölçülen | Hedef | Durum |
|---|---|---|---|
| F1 kazancı (GraphRAG vs vektör RAG) | -%13,0 (GraphRAG 0,443, vektör 0,509) | ≥ +%20 | Karşılanmadı |
| Uydurma atıf oranı (GraphRAG) | %0 | < %5 | Karşılandı |
| p@95 gecikme (GraphRAG) | 27,4 sn (ortanca 16,6 sn; vektör RAG p95 8,1 sn) | < 2,5 sn | Karşılanmadı |

### Türlere göre F1

| Tür | Soru | GraphRAG | Vektör RAG |
|---|---|---|---|
| Tek adım | 10 | 0,824 | 0,967 |
| İki adım | 15 | 0,461 | 0,486 |
| Üç adım | 10 | 0,196 | 0,232 |
| Çelişki | 5 | 0,123 | 0,219 |
| Tümü | 40 | 0,443 | 0,509 |

Soru bazında puanlar: `results/puanlar.csv`.

## Değerlendirme

Hedeflerden yalnızca uydurma atıf oranı karşılandı. GraphRAG'in vektör RAG'e kazancı beklenen +%20 yerine -%13 çıktı.

**Gözlemler**
1. Tek turda 0,035'ten 0,443'e çıkış, grafın tek başına yetmediğini gösterdi: soruların çoğu rakam, tarih, tutar istiyor ve bunlar ilişki olarak grafa girmiyor. Graf bir dizin olarak (hangi sayfalara bakılacak) kullanıldığında sonuç yükseldi.
2. Doğru kanıt sayfası GraphRAG'in atıflarında yalnızca 14/40 soruda görünüyor. Darboğaz cevap üretimi değil, graftan doğru sayfaya ulaşmak. Yerel 8B modelin sayfa başına yaklaşık 5 ilişki çıkarması bazı sayfaları grafta görünmez bırakıyor.
3. Çok adımlı (üç adım ve çelişki) sorularda her iki sistem de zayıf; GraphRAG'in beklenen üstünlüğü bu türlerde ortaya çıkmadı. Kelime düzeyinde F1 uzun, çok parçalı cevapları cezalandırdığı için mutlak değerler düşük kalıyor.
4. Gecikme hedefi 8B yerel modelle gerçekçi değildi. Her soruda iki model çağrısı yapılıyor (sorudaki varlıkları bulma, cevap üretme).

**Sonraki adımlar (Hafta 4)**
- Hibrit erişim: graf ile bulunan sayfalara ek olarak vektör araması sonuçlarını birleştirmek.
- Çıkarım kalitesini artırmak (daha güçlü model ya da API modeli ile ilişki çıkarımı), böylece grafın sayfa kapsamı genişler.
- Varlık bulma çağrısını modelsiz yapıp gecikmeyi düşürmek.

## Hafta 4 güncellemesi (25 Kasım 2026)

Atıf doğrulaması düzeltildikten sonra 40 soru aynı donanımda yeniden ölçüldü (`python -m src.graphrag.degerlendir`, ardından `python -m src.olcum.run`).

| Metrik | Hafta 3 | Atıf esnetildikten sonra (hatalı) | Hafta 4 son | Hedef |
|---|---|---|---|---|
| F1 farkı (GraphRAG vs vektör) | −%13 (0,443 / 0,509) | −%13 | −%13 (0,443 / 0,509) | ≥ +%20 |
| Uydurma atıf oranı | %0 | **%9,4** | **%0** | < %5 |
| p95 gecikme | 27,4 sn | 21,6 sn | 20,7 sn | < 2,5 sn |

**Ne oldu:** Atıf doğrulaması esnetildi (büyük/küçük harf, noktalama ve "..." ile kesik alıntılar kabul edildi) ama kabul edilen atıf, modelin yazdığı biçimle saklandı. Ölçüm aracı alıntıyı kaynakta birebir aradığı için bu atıfları uydurma saydı ve oran %9,4'e çıktı. Düzeltme: kabul edilen atıf artık kaynak sayfadaki birebir metinle döner (`alinti_bul`). Oran %0'a indi.

**Sonuç:** Cevaplar değişmediği için F1 aynı kaldı. Gecikme biraz düştü (27,4 sn → 20,7 sn). Bu hafta gecikmeyi düşürecek bir değişiklik yapmadık, soru başına hâlâ iki model çağrısı var; fark büyük ihtimalle Ollama'nın ısınmış olmasından ve ölçüm oynamasından geliyor. Hedefin çok üstünde. F1 farkı ve gecikme hedefleri hâlâ karşılanmıyor; bunlar yukarıdaki "Sonraki adımlar"a bağlı (hibrit erişim, daha güçlü model, modelsiz varlık bulma).

**Ders:** Bir doğrulama kuralını gevşetirken ölçüm aracının kendi kuralıyla aynı çıktıyı kabul ettiğini test etmek gerekiyor (`test_kabul_edilen_atif_olcum_aracinin_kati_kontrolunu_da_gecer`).
