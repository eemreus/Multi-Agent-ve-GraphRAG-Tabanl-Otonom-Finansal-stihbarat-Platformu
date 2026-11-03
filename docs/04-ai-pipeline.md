# AI Pipeline Diyagramı



Bir kullanıcı sorgusunun raporlanmış brifinge dönüşene kadar geçtiği model aşamaları ve aralarında akan veri biçimleri. Pahalı API modeli yalnızca planlama, sorgu üretimi ve rapor yazımında kullanılır. Standart çıkarım işleri yerel modelde (Ollama, Llama 3) çalışır. Doğrulama aşamasında dil modeli yerine embedding ve kural tabanlı kontroller kullanılır. İlgili isterler: REQ-01, REQ-02, REQ-04, REQ-06.



```mermaid

flowchart TB

    subgraph S1 ["1. Planlama"]

        Q(["Kullanıcı sorgusu"]) --> PLAN["Orkestratör Ajan<br/>Yönlendirici Model, API<br/>alt sorgu listesi, JSON"]

    end



    subgraph S2 ["2. Veri toplama"]

        RES["Araştırma Ajanı<br/>SearXNG ve Trafilatura<br/>model kullanılmaz"]

    end



    subgraph S3 ["3. Bilgi çıkarımı"]

        CHUNK["Metni parçala<br/>kaynak kimliği korunur"]

        NER["Bilgi Çıkarım Ajanı<br/>Yerel Model, Ollama<br/>varlık ve ilişki çıkarımı"]

        SCHEMA{"Çıktı şemaya<br/>uyuyor mu?"}

        DEDUP["Varlık eşleştirme<br/>aynı şirketin farklı yazımları"]

        CHUNK --> NER --> SCHEMA

        SCHEMA -->|Evet| DEDUP

        SCHEMA -->|Hayır, en fazla 2 tekrar| NER

        SCHEMA -->|2 tekrardan sonra hâlâ geçersiz| ESC["Chunk bir kez<br/>Yönlendirici Modele, API<br/>yükseltilir"]

        ESC --> SCHEMA2{"Çıktı şemaya<br/>uyuyor mu?"}

        SCHEMA2 -->|Evet| DEDUP

        SCHEMA2 -->|Hayır| SKIP["Chunk atlanır<br/>başarısız olarak loglanır"]

    end



    subgraph S4 ["4. Bilgi grafiği"]

        NEO[("Neo4j<br/>düğüm ve ilişki<br/>her ilişkide source_id")]

    end



    subgraph S5 ["5. GraphRAG sorgusu"]

        T2C["Sorgudan Cypher üret<br/>Yönlendirici Model, API"]

        CYP["Cypher çalıştır<br/>derinlik en fazla 3"]

        RED[("Redis<br/>sorgu cache")]

        T2C --> CYP

        CYP <-.-> RED

    end



    subgraph S6 ["6. Doğrulama"]

        XV["Doğrulama Ajanı<br/>çapraz kaynak karşılaştırma<br/>dairesel raporlama tespiti"]

        SCORE["Güven puanı<br/>kaynak türü, güncellik,<br/>yayıncı geçmişi"]

        XV --> SCORE

    end



    subgraph S7 ["7. Raporlama"]

        WRITE["Raporlama Ajanı<br/>Yönlendirici Model, API<br/>kaynaklı brifing taslağı"]

        CITE["Atıf doğrulama<br/>Embedding Modeli<br/>benzerlik eşiği 0.75"]

        WRITE --> CITE

    end



    PLAN -->|alt sorgular| RES

    RES -->|ham metin ve URL| CHUNK

    DEDUP -->|MERGE ile yaz| NEO

    NEO -->|bilgi eksikse yeni sorgu| PLAN

    NEO --> T2C

    CYP -->|ilgili alt graf| XV

    SCORE -->|puanlı bulgular, çelişkiler| WRITE

    CITE -->|doğrulanmış rapor| OUT(["Güvenilirlik damgalı brifing"])

    CITE -.->|atıf başarısızsa yeniden yaz, en fazla 2 tur| WRITE



    BUDGET["Token bütçesi<br/>API modeli çağrılarında kontrol"] -.-> PLAN

    BUDGET -.-> T2C

    BUDGET -.-> WRITE

    LOG["Loglama ve Telemetri<br/>token, gecikme, hata, atıf sayacı"]

    S2 -.-> LOG

    S3 -.-> LOG

    S5 -.-> LOG

    S6 -.-> LOG

    S7 -.-> LOG

```



## Hangi aşamada hangi model



| Aşama | Model | Neden |
|-------|-------|-------|
| Planlama | Yönlendirici Model (API) | Alt sorgu üretimi akıl yürütme gerektirir |
| Veri toplama | Yok | Arama ve metin çekme araç işi |
| Bilgi çıkarımı | Yerel Model (Ollama, Llama 3). Şema 2 tekrarda tutmazsa chunk bir kez API modeline yükseltilir | Yüksek hacim, standart görev, token maliyeti sıfır. Yükseltme yalnızca zor chunk'lar için, maliyet düşük kalır |
| Sorgudan Cypher | Yönlendirici Model (API) | Hatalı sorgu graf sonucunu bozar, kaliteli model gerekir |
| Doğrulama | Model yok, kural ve puanlama | Tekrarlanabilir ve ölçülebilir olması için |
| Raporlama | Yönlendirici Model (API) | Kullanıcının gördüğü çıktı |
| Atıf doğrulama | Embedding Modeli | İddia ve kaynak metin benzerliği |



## Veri biçimleri



- Planlama çıkışı: `{"alt_sorgular": [...], "butce": {...}}`

- Çıkarım çıkışı: `{"varliklar": [...], "iliskiler": [{"kaynak", "tur", "hedef", "source_id"}]}`

- Doğrulama çıkışı: her bulgu için `guven_puani`, `celiski_var`, `kaynak_sayisi`

- Rapor: her iddia için `source_id`, URL ve erişim tarihi

