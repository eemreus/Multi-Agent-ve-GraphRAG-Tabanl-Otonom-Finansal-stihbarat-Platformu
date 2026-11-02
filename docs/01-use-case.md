# Use Case Diyagramı

Mermaid'de yerel use case diyagramı bulunmadığı için `flowchart` ile gösterilmiştir. Aktörler yuvarlak, use case'ler oval, sistem sınırı kutu olarak çizilmiştir.

```mermaid
flowchart LR
    ANA([Analist])
    ADM([Yönetici])
    KUR([Harici Kurumsal Yazılım])

    subgraph SYS [Otonom Finansal İstihbarat Platformu]
        direction TB
        UC1(Araştırma sorgusu gönder)
        UC2(Araştırma ilerlemesini izle)
        UC3(Brifing raporunu görüntüle)
        UC4(İddia kaynağını ve güven puanını incele)
        UC5(Çelişki ve düşük güven uyarılarını gör)
        UC6(Bilgi grafiğini keşfet)
        UC7(Geçmiş araştırmalara eriş)
        UC8(Raporu dışa aktar)
        UC9(Araştırmayı iptal et / durdur)
        UC10(Kullanıcı ve yetki yönetimi)
        UC11(Token bütçesi ve model ayarlarını yönet)
        UC12(Sistem loglarını ve telemetriyi izle)
        UC13(API üzerinden sorgu gönder)
        UC14(Giriş yap / kayıt ol)
    end

    SEA([SearXNG / Web])
    KAP([KAP API / RSS])
    LLM([LLM: Ollama / API])
    NEO([Neo4j Graf DB])

    ANA --- UC14
    ANA --- UC1
    ANA --- UC2
    ANA --- UC3
    ANA --- UC4
    ANA --- UC5
    ANA --- UC6
    ANA --- UC7
    ANA --- UC8
    ANA --- UC9

    ADM --- UC10
    ADM --- UC11
    ADM --- UC12

    KUR --- UC13

    UC1 -. include .-> UC2
    UC3 -. include .-> UC4
    UC3 -. extend: çelişki varsa .-> UC5
    UC13 -. include .-> UC1

    UC1 --- SEA
    UC1 --- KAP
    UC1 --- LLM
    UC1 --- NEO
    UC6 --- NEO
```

## Aktörler

| Aktör | Tür | Açıklama |
|-------|-----|----------|
| Analist | Birincil | Araştırma sorusunu girer, brifingi okur, kaynakları inceler |
| Yönetici | Birincil | Kullanıcıları, bütçeyi ve model ayarlarını yönetir, logları izler |
| Harici Kurumsal Yazılım | İkincil | Platformu REST API üzerinden çağıran diğer sistemler (REQ-05) |
| SearXNG / Web | Dış sistem | Güncel web kaynaklarını sağlar |
| KAP API / RSS | Dış sistem | Resmi bildirimler ve doğrulanmış besleme (bot engeli durumunda yedek) |
| LLM (Ollama / API) | Dış sistem | Alt sorgu üretimi, varlık-ilişki çıkarımı, rapor yazımı |
| Neo4j | Dış sistem | Bilgi grafiği depolama ve GraphRAG sorguları |

## Use case – ister eşlemesi

| Use case | İlgili ister |
|----------|--------------|
| UC1, UC2, UC9 | REQ-01 Otonom Tarama |
| UC6 | REQ-02 Dinamik Ağ Kurulumu |
| UC3, UC4, UC8 | REQ-03 Şeffaf Kaynak Gösterimi |
| UC5 | REQ-04 Güvenilirlik Damgası |
| UC13, UC12 | REQ-05 Düşük Gecikmeli API Servisi |
| UC4 (atıf denetimi) | REQ-06 Kaynak Denetimi ve Güvenlik |
