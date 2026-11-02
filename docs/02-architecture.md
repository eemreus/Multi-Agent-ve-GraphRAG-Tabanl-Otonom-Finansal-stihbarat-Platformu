# Sistem Mimarisi

Öneri formundaki dört katman (arama, çıkarım, doğrulama, raporlama), mikro servisler ve altyapı bileşenleriyle birlikte gösterilmiştir.

```mermaid
flowchart TB
    subgraph CLIENT [İstemci Katmanı]
        FE[Web Arayüzü<br/>React / Next.js]
        EXT[Harici Kurumsal Yazılımlar]
    end

    subgraph GW [API Katmanı]
        API[FastAPI Gateway<br/>Auth, Rate Limit, Swagger]
    end

    subgraph AGENTS [Ajan Katmanı - Mikro Servisler]
        ORC[Orkestratör Ajan<br/>Alt sorgu üretimi, ReAct döngüsü,<br/>bilgi kazancı ile durma]
        RES[Araştırma Ajanı<br/>Katman 1]
        EXTR[Bilgi Çıkarım Ajanı<br/>Katman 2]
        VER[Doğrulama Ajanı<br/>Katman 3]
        REP[Raporlama Ajanı<br/>Katman 4]
    end

    subgraph TOOLS [Veri Toplama Araçları]
        SX[SearXNG]
        TF[Trafilatura]
        KAP[KAP API / RSS<br/>yedek kaynak]
        PRX[Proxy Rotasyonu]
    end

    subgraph MODELS [Model Katmanı]
        LLMR[Yönlendirici Model<br/>API]
        LLML[Yerel Model<br/>Ollama / Llama 3]
        EMB[Embedding Modeli<br/>atıf benzerlik kontrolü]
    end

    subgraph STORE [Depolama Katmanı]
        NEO[(Neo4j<br/>Bilgi Grafiği)]
        PG[(PostgreSQL<br/>kullanıcı, oturum, iddia,<br/>kaynak, log)]
        RED[(Redis<br/>cache, görev kuyruğu)]
        SNAP[(Anlık Görüntü Deposu<br/>dondurulmuş web sayfaları)]
    end

    subgraph OBS [İzleme]
        LOG[Loglama ve Telemetri<br/>token, gecikme, hata]
    end

    FE --> API
    EXT --> API
    API --> ORC
    API --> PG

    ORC --> RES
    RES --> SX
    RES --> TF
    RES -. bot engeli .-> PRX
    RES -. fallback .-> KAP
    RES --> SNAP
    RES -->|ham metin| EXTR

    EXTR --> LLML
    EXTR -->|düğüm ve ilişki| NEO
    EXTR -->|bilgi eksikse| ORC

    ORC --> LLMR
    NEO <-->|GraphRAG sorgusu| VER
    VER --> EMB
    VER --> PG
    VER -->|güven puanı, çelişkiler| REP
    REP --> LLMR
    REP -->|rapor| PG
    REP --> API

    ORC <--> RED
    API <--> RED

    ORC -.-> LOG
    RES -.-> LOG
    EXTR -.-> LOG
    VER -.-> LOG
    REP -.-> LOG
    LOG --> PG
```

## Bileşen açıklamaları

| Bileşen | Sorumluluk | İlgili ister |
|---------|------------|--------------|
| FastAPI Gateway | Kimlik doğrulama, istek yönlendirme, Swagger dokümantasyonu | REQ-05 |
| Orkestratör Ajan | Sorguyu alt sorulara böler, ReAct döngüsünü yönetir, bilgi kazancı eşiği ve token bütçesiyle durdurur | REQ-01 |
| Araştırma Ajanı | SearXNG ile arar, Trafilatura ile metni çeker, bot engelinde proxy ve KAP/RSS yedeğine geçer | REQ-01 |
| Bilgi Çıkarım Ajanı | Metinden varlık ve ilişkileri çıkarır, Neo4j'ye düğüm ve ilişki olarak yazar | REQ-02 |
| Doğrulama Ajanı | Çapraz doğrulama, dairesel raporlama tespiti, yayıncı güven puanı, atıf-metin benzerlik kontrolü | REQ-04, REQ-06 |
| Raporlama Ajanı | Tıklanabilir kaynak, erişim tarihi ve güven damgalı brifing üretir | REQ-03, REQ-04 |
| Neo4j | Bilgi grafiği ve multi-hop GraphRAG sorguları (derinlik 2-3 ile sınırlı) | REQ-02 |
| PostgreSQL | Kullanıcı, oturum, kaynak, iddia, atıf ve metrik kayıtları | REQ-03, REQ-05 |
| Redis | Sık sorulan ilişkiler için cache, ajanlar arası görev kuyruğu | Risk planı (gecikme) |
| Anlık Görüntü Deposu | Çekilen sayfaların dondurulmuş kopyaları, test kümesi için temel | Çıktı: dondurulmuş test kümesi |
| Loglama ve Telemetri | Token kullanımı, p@95 gecikme, uydurma atıf oranı ölçümü | REQ-05, REQ-06 |

## Tasarım kararları

- **Hibrit depolama:** İlişkisel veri (kullanıcı, oturum, log) PostgreSQL'de, bilgi grafiği Neo4j'de tutulur. Her graf ilişkisi `source_id` ile PostgreSQL'deki kaynak kaydına bağlanır.
- **Model ayrımı:** Pahalı API modeli yalnızca orkestratör ve rapor yazımında, standart çıkarım işleri yerel modelde çalışır (token maliyeti riski için B planı).
- **Fallback zinciri:** Bot engeli → proxy değişimi → KAP API / RSS beslemesi.
- **Her ajan ayrı servis:** Bağımsız ölçeklenebilir, bağımsız loglanabilir ve test edilebilir (REQ-05).
