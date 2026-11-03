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

Araştırma Ajanı alt sorguyu önce Redis cache'te arar (anahtar: normalize edilmiş sorgu ve URL, TTL 1 saat). Bulamazsa SearXNG ile URL listesi çıkarır ve her URL için Trafilatura ile metni çeker. Hataya göre yol ayrılır: bot engelinde proxy rotasyonu (en fazla 3 deneme), 404 veya boş sayfada sıradaki URL, zaman aşımında bir tekrar denemeden sonra sıradaki URL. URL listesi biterse KAP API ve doğrulanmış RSS yedeğine geçilir. Çekilen her sayfa anlık görüntü olarak saklanır (dondurulmuş test kümesinin temeli). İlgili isterler: REQ-01, REQ-06.

```mermaid
flowchart TD
    IN(["Orkestratör: alt sorgu"]) --> CACHE{"Redis cache'te<br/>sonuç var mı?"}
    CACHE -->|Evet| OUT
    CACHE -->|Hayır| SX["SearXNG<br/>arama, URL listesi"]
    SX --> TF["Trafilatura<br/>sıradaki URL'in metnini çek"]
    TF --> OK{"İçerik alındı mı?"}

    OK -->|Evet| SNAP[("Anlık Görüntü Deposu<br/>dondurulmuş sayfa kopyası")]
    SNAP --> PG[("PostgreSQL<br/>kaynak kaydı, erişim tarihi")]
    PG --> OUT(["Ham metin ve kaynak bilgisi<br/>Bilgi Çıkarım Ajanı'na"])
    PG -.->|cache'e yaz| RED[("Redis cache")]

    OK -->|Hayır| ERR{"Hata türü"}
    ERR -->|bot engeli: 403, captcha| PRX["Proxy Rotasyonu<br/>yeni proxy ile dene"]
    PRX --> RETRY{"Deneme sayısı<br/>3'e ulaştı mı?"}
    RETRY -->|Hayır| TF
    RETRY -->|Evet| MORE
    ERR -->|zaman aşımı| TO{"İlk zaman aşımı mı?"}
    TO -->|Evet, bir kez tekrar dene| TF
    TO -->|Hayır| MORE
    ERR -->|404 veya boş sayfa| MORE

    MORE{"Listede başka<br/>URL var mı?"}
    MORE -->|Evet| TF
    MORE -->|Hayır| FB["Yedek kaynak<br/>KAP API ve doğrulanmış RSS"]
    FB --> FOK{"Yedekten içerik<br/>alındı mı?"}
    FOK -->|Evet| SNAP
    FOK -->|Hayır| FAIL(["Kaynak alınamadı<br/>Orkestratör'e bildirilir"])

    TF -.-> LOG["Loglama ve Telemetri<br/>hata türü, deneme sayısı, gecikme"]
    PRX -.-> LOG
    FB -.-> LOG
```

## Akış 4 (bonus): Atıf doğrulama

Raporlama Ajanı'nın ürettiği taslaktaki her atıf, yayımlanmadan önce iki kontrolden geçer. Birincisi varlık kontrolü: atıf yapılan kaynak gerçekten çekilmiş ve kayıtlı mı? İkincisi anlam kontrolü: iddia ile kaynak metni arasındaki embedding benzerliği eşiğin üstünde mi (başlangıç eşiği 0.75, dondurulmuş test kümesinde kalibre edilecek)? Kontrolü geçemeyen iddia taslaktan çıkarılır ya da yeniden yazılır (en fazla 2 tur). Uydurma atıf oranı log kayıtlarından ölçülür, hedef %5'in altı. İlgili isterler: REQ-06, REQ-03.

```mermaid
flowchart TD
    DRAFT(["Raporlama Ajanı: taslak rapor"]) --> EXT["Atıfları ve iddiaları ayıkla<br/>iddia, kaynak URL çiftleri"]
    EXT --> EXIST{"Kaynak kayıtlı mı?<br/>PostgreSQL ve Anlık Görüntü Deposu"}

    EXIST -->|Hayır| FAKE["Uydurma atıf<br/>birinci sınıf hata"]
    EXIST -->|Evet| SIM["Embedding Modeli<br/>iddia ile kaynak metni benzerliği"]
    SIM --> THR{"Benzerlik 0.75<br/>ve üstü mü?"}

    THR -->|Evet| PASS["Atıf doğrulandı"]
    THR -->|Hayır| WEAK["Zayıf destek<br/>iddia işaretlenir"]

    FAKE --> LOGF["Loglama ve Telemetri<br/>uydurma atıf sayacı"]
    WEAK --> LOGF
    PASS --> LOGP["Loglama ve Telemetri<br/>doğrulanan atıf sayacı"]

    FAKE --> FIX{"Yeniden yazma<br/>2 turu doldu mu?"}
    WEAK --> FIX
    FIX -->|Hayır| REW["Raporlama Ajanı<br/>iddiayı kaldır veya kaynağa uygun yaz"]
    REW --> EXT
    FIX -->|Evet| DROP["İddia rapordan çıkarılır<br/>veya düşük güven uyarısı eklenir"]

    PASS --> FINAL
    DROP --> FINAL(["Doğrulanmış rapor<br/>her iddia kaynaklı"])
    LOGF -.-> METRIC[("PostgreSQL<br/>uydurma atıf oranı = uydurma / toplam")]
    LOGP -.-> METRIC
```