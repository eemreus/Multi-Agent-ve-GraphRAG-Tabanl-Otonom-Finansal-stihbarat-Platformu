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