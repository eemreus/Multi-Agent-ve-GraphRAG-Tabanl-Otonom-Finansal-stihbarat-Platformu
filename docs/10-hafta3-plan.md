# Hafta 3 Planı: Veri + AI Baseline (Demo)

Dersin Hafta 3 teslimi: veri hazır, EDA notebook'u, değerlendirme için ayrılmış test seti, ilk AI prototipi (baseline), ilk metriklerin öneri formundaki nicel hedeflerle karşılaştırılması. Kontrol: sınıfta 5 dk sunum (demo).

## Şirket seçimi

Dört çekirdek şirket: **Türk Hava Yolları (THYAO), Pegasus (PGSUS), Koç Holding (KCHOL), Sabancı Holding (SAHOL)**. Bu şirketlerin iştirakleri (Ford Otosan, Tüpraş, Yapı Kredi, Enerjisa, Akbank gibi) açıklamalarda geçtiği için grafa kendiliğinden girer, ayrıca toplanmaz.

| Seçim nedeni | Nasıl yardım eder |
|--------------|-------------------|
| İki rakip çift: THY–Pegasus ve Koç–Sabancı | `COMPETITOR_OF` ilişkisi ve "rakiplerin ortak noktası" tipi sorular |
| Holdinglerin ortak girişimleri (örneğin Enerjisa, Ford Otosan, Yapı Kredi) | `PARTICIPATED_IN` ve çok adımlı sorular |
| Yönetim kurulu değişiklikleri sık ve KAP'ta düzenli açıklanıyor | `BOARD_MEMBER_OF` ilişkisi, zaman aralıklı sorular |
| Büyük şirketler, haberleri çok kaynakta yer alıyor | Dairesel raporlama ve çelişki örnekleri doğal olarak çıkar |
| Türkçe KAP bildirimleri ve haberler | Yerel modelin Türkçe varlık çıkarımı gerçek veride denenir |

Küçük tutuldu: 4 şirket ile 150+ belge hem elle etiketlenebilir hem yerel modelle işlenebilir.

## Test seti

40 sayfa dondurulur, 40 soru-cevap çifti yazılır: 10 tek adımlı, 15 iki adımlı, 10 üç adımlı, 5 çelişki veya dairesel raporlama sorusu. Her cevabın kanıt cümlesi ve kaynağı kayıtlıdır. Test seti geliştirme sırasında ayarlama için kullanılmaz.

## Ölçülecek metrikler (öneri formundaki hedefler)

| Metrik | Hedef |
|--------|-------|
| Yanıt doğruluğu (F1) | Vektör RAG'e göre en az %20 artış |
| Uydurma atıf oranı | %5'in altı |
| p@95 gecikme | 2500 ms'nin altı |

## Görevler

| Görev | Sorumlu | Issue |
|-------|---------|-------|
| H3-1 Veri toplama hattı | Sıla | [#18](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/18) |
| H3-2 Dondurulmuş test seti ve etiketleme | Sıla (toplama), Emre + Sıla (etiket) | [#19](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/19) |
| H3-3 EDA notebook'u | Emre | [#20](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/20) |
| H3-4 Neo4j ve varlık-ilişki çıkarımı | Emre | [#21](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/21) |
| H3-5 GraphRAG baseline | Emre | [#22](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/22) |
| H3-6 Vektör RAG baseline | Sıla | [#23](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/23) |
| H3-7 Ölçüm ve hedef tablosu | Emre | [#24](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/24) |
| H3-8 Açık teknoloji kararları | Sıla | [#25](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/25) |
| H3-9 5 dk demo sunumu | Emre + Sıla | [#26](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/26) |

## Donanım notu

Yerel model Emre'nin RTX 3060 ekran kartında çalışacak. Model boyutu H3-8'deki deneyle seçilir. Yetmezse çıkarım ilk aşamada API modeliyle yapılır.
