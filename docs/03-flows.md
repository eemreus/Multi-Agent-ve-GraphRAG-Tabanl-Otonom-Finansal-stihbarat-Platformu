# Akış Diyagramları

## Akış 1: Uçtan uca sorgu → brifing (ReAct + durma ölçütü)

Kullanıcı sorgusu alt sorulara bölünür. Araştırma döngüsü ReAct mantığıyla (düşün, eylem yap, gözlemle) ilerler ve iki durma ölçütünden biri tetiklenince biter: bilgi kazancının eşiğin altına düşmesi ya da döngü ve token bütçesinin dolması. Bot engeli gibi hatalarda Akış 2 devreye girer. Doğrulama sonrası çelişki veya düşük güven varsa rapora açık uyarı eklenir. İlgili isterler: REQ-01, REQ-03, REQ-04.

```mermaid
flowchart TD
    U(["Kullanıcı sorgusu"]) --> API["FastAPI Gateway<br/>kimlik doğrulama, oturum kaydı"]
    API --> ORC1["Orkestratör Ajan<br/>sorguyu alt sorulara böler"]
    ORC1 -->|düşün| BUDGET{"Döngü ve token<br/>bütçesi doldu mu?"}

    BUDGET -->|Hayır, eylem: ara| RES["Araştırma Ajanı<br/>SearXNG ile ara,<br/>Trafilatura ile metni çek"]
    RES -->|ham metin| EXTR["Bilgi Çıkarım Ajanı<br/>varlık ve ilişki çıkarır"]
    RES -->|başarısız: bot engeli| FLOW2["Akış 2<br/>proxy rotasyonu,<br/>KAP API ve RSS yedeği"]
    FLOW2 -->|içerik alındı| EXTR
    FLOW2 -->|kaynak alınamadı| ORC2

    EXTR --> NEO[("Neo4j<br/>Bilgi Grafiği")]
    NEO -.->|sık sorulan ilişkiler| RED[("Redis<br/>cache")]
    NEO -->|gözlem| GAIN{"Bilgi kazancı<br/>eşiğin altında mı?"}

    GAIN -->|Hayır, bilgi eksik| ORC2["Orkestratör<br/>yeni alt sorgu üretir"]
    ORC2 --> BUDGET

    GAIN -->|Evet, yeterli| VER
    BUDGET -->|Evet, bütçe bitti| VER["Doğrulama Ajanı<br/>çapraz doğrulama,<br/>dairesel raporlama kontrolü,<br/>güven puanı"]

    VER --> CONF{"Kaynaklar çelişiyor mu<br/>veya güven düşük mü?"}
    CONF -->|Evet| WARN["Çelişki ve düşük güven<br/>uyarısı eklenir"]
    CONF -->|Hayır| REP
    WARN --> REP["Raporlama Ajanı<br/>her iddia için tıklanabilir<br/>kaynak ve erişim tarihi"]
    REP --> OUT(["Güvenilirlik damgalı brifing"])

    ORC1 -.-> LOG["Loglama ve Telemetri<br/>token, gecikme, hata"]
    RES -.-> LOG
    EXTR -.-> LOG
    VER -.-> LOG
    REP -.-> LOG
```


## Akış 2: Web tarama ve içerik çekme (bot engeli, fallback)

Araştırma Ajanı, Orkestratör'den gelen alt sorguyu önce cache'te arar, bulamazsa SearXNG ile arar ve Trafilatura ile sayfa metnini çeker. Bot engelinde proxy rotasyonu denenir, sorun sürerse KAP API ve doğrulanmış RSS beslemelerine geçilir. Çekilen her sayfa anlık görüntü olarak saklanır (test kümesinin temeli). İlgili ister: REQ-01, REQ-06.

```mermaid
flowchart TD
    IN(["Orkestratör: alt sorgu"]) --> CACHE{"Redis cache'te<br/>sonuç var mı?"}
    CACHE -->|Evet| OUT
    CACHE -->|Hayır| SX["SearXNG<br/>arama, URL listesi"]
    SX --> TF["Trafilatura<br/>sayfa metnini çek"]
    TF --> OK{"İçerik alındı mı?"}

    OK -->|Evet| SNAP[("Anlık Görüntü Deposu<br/>dondurulmuş sayfa kopyası")]
    SNAP --> PG[("PostgreSQL<br/>kaynak kaydı, erişim tarihi")]
    PG --> OUT(["Ham metin ve kaynak bilgisi<br/>Bilgi Çıkarım Ajanı'na"])

    OK -->|Hayır| BOT{"Bot engeli mi?<br/>Cloudflare, 403, captcha"}
    BOT -->|Hayır, başka hata| FB
    BOT -->|Evet| PRX["Proxy Rotasyonu<br/>yeni proxy ile tekrar dene"]
    PRX --> RETRY{"Deneme sınırı<br/>aşıldı mı?"}
    RETRY -->|Hayır| TF
    RETRY -->|Evet| FB["Yedek kaynak<br/>KAP API ve doğrulanmış RSS"]

    FB --> FOK{"Yedekten içerik<br/>alındı mı?"}
    FOK -->|Evet| SNAP
    FOK -->|Hayır| FAIL(["Kaynak alınamadı<br/>Orkestratör'e bildirilir"])

    TF -.-> LOG["Loglama ve Telemetri<br/>hata türü, deneme sayısı, gecikme"]
    PRX -.-> LOG
    FB -.-> LOG
```