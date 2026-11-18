# 12 - Teknoloji Kararları (Hafta 3, #25)

Durum: **Onaylandı** (Sıla ve Emre). Hazırlayan: Sıla.

Bu belge dört açık kararı gerekçesiyle kayda geçirir. Her karar için seçilen seçenek, neden seçildiği, elenen alternatif ve bilinen risk yazılıdır.

## 1. Ajan çerçevesi: LangGraph

| | LangGraph | AutoGen |
|---|---|---|
| Çalışma mantığı | Adımlar bir **graf** (düğüm + kenar) olarak tanımlanır, durum düğümler arasında taşınır | Ajanlar birbiriyle **sohbet ederek** iş çözer |
| Akış kontrolü | Koşullu kenar ve döngü açıkça yazılır (ör. "kaynak yetersizse tekrar ara") | Akış sohbetin gidişatına bırakılır, öngörmesi zor |
| Bizim ihtiyaç | Planlayıcı, Araştırmacı, Doğrulayıcı gibi **sabit sıralı** adımlar ve ölçülebilir gecikme | Serbest tartışma gerekmiyor |

**Karar:** LangGraph.
**Gerekçe:** `docs/04-ai-pipeline.md` içindeki akış zaten bir durum makinesi. Her düğümün süresini ayrı ölçebilmek p95 gecikme hedefi (2500 ms altı) için gerekli.
**Risk:** Öğrenme eğrisi. Ayrıca yerel 8B modelle cevap üretim aşamasında p95 < 2500 ms hedefi zorlanabilir (çıkarım çevrimdışıdır, sorun değil); ölçümde ayrı raporlanır. Önce tek düğümlü basit bir graf ile başlanır.

## 2. Yerel model: Ollama üzerinden 7-8B sınıfı model

**Karar:** Ollama ile çalışan `llama3.1:8b`. Türkçe çıkarım zayıf kalırsa `qwen2.5:7b` denenir.
**Gerekçe:** Varlık-ilişki çıkarımı toplu iş (yaklaşık 297 model çağrısı) ve veri dışarı çıkmıyor. 8B model tek tüketici ekran kartında çalışır.
**Elenen:** 13B ve üzeri modeller, ekran kartı belleğine sığmama riski.
**Not:** Ekran kartı belleği (RTX 3060: 6 mı 12 GB mı) ilk denemede doğrulanır; 6 GB ise `llama3.2:3b` ya da API modeli yedeği kullanılır.
**Risk:** Türkçe finansal metinde hata oranı. Çözüm: aynı 40 sayfalık test seti üzerinde iki modeli karşılaştırıp F1'e göre seçmek.
**Açık nokta:** Emre'nin `src/graf/extractor.py` dosyasında hangi model adı kullanılıyorsa belge ona göre eşitlenecek.

## 3. API modeli: hakem ve kalite referansı olarak

**Karar:** Yerel model **ana hat** olarak kalır. API modeli yalnızca (a) cevap kalitesini puanlayan hakem ve (b) yerel modelin zorlandığı sorularda karşılaştırma referansı olarak kullanılır.
**Gerekçe:** Maliyet ve gizlilik kontrolü. Ana hat yerelde olunca p95 gecikme ve tekrarlanabilirlik bizim elimizde.
**Risk:** API maliyeti. Çözüm: yalnızca 40 sayfa / 40 soruluk dondurulmuş test setiyle sınırlı çağrı, sonuçlar önbelleğe alınır.

## 4. Gözlem aracı: Langfuse

| | Langfuse | LangSmith |
|---|---|---|
| Barındırma | Açık kaynak, Docker ile kendi makinemizde | Bulut hizmeti |
| Maliyet | Ücretsiz (kendi barındırma) | Ücretsiz katman sınırlı |
| Bize uygunluk | Veri dışarı çıkmaz, `docker-compose.yml`'a eklenir | Hesap ve kota yönetimi gerekir |

**Karar:** Langfuse.
**Gerekçe:** Her çağrının süresini ve girdi/çıktısını kaydeder. Bu kayıt hem p95 gecikme ölçümünün (#24) hem de uydurma atıf oranının kanıtı olur.
**Risk:** Ek bir konteyner ve bellek yükü. Gerekirse yalnızca ölçüm günlerinde açılır.

## Ölçüt bağlantısı

| Hedef | Bu kararların katkısı |
|---|---|
| F1, vektör RAG'den en az %20 yüksek | LangGraph ile çok adımlı arama, aynı yerel model her iki tarafta |
| Uydurma atıf oranı %5 altı | Doğrulayıcı düğüm + Langfuse izleri |
| p95 gecikme 2500 ms altı | Düğüm başına süre ölçümü, yerel model |

## Onay

- [x] Sıla
- [x] Emre
