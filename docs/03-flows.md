# Akış Diyagramları



## Akış 1: Uçtan uca sorgu → brifing (ReAct + durma ölçütü)



Kullanıcı sorgusu alt sorulara bölünür, araştırma döngüsü iki durma ölçütünden biri tetiklenene kadar sürer. İlgili ister: REQ-01, REQ-03, REQ-04.



```mermaid

flowchart TD

    U([Kullanıcı sorgusu]) --> API[FastAPI Gateway<br/>kimlik doğrulama]

    API --> ORC1[Orkestratör Ajan<br/>sorguyu alt sorulara böler]

    ORC1 --> BUDGET{Döngü ve token<br/>bütçesi doldu mu?}



    BUDGET -- Hayır --> RES[Araştırma Ajanı<br/>SearXNG ile ara,<br/>Trafilatura ile metni çek]

    RES --> EXTR[Bilgi Çıkarım Ajanı<br/>varlık ve ilişki çıkarır]

    EXTR --> NEO[(Neo4j<br/>Bilgi Grafiği)]

    NEO --> GAIN{Bilgi kazancı<br/>eşiğin altında mı?}



    GAIN -- Hayır, bilgi eksik --> ORC2[Orkestratör<br/>yeni alt sorgu üretir]

    ORC2 --> BUDGET



    GAIN -- Evet, yeterli --> VER

    BUDGET -- Evet, bütçe bitti --> VER[Doğrulama Ajanı<br/>çapraz doğrulama,<br/>güven puanı]



    VER --> REP[Raporlama Ajanı<br/>kaynak bağlantılı brifing]

    REP --> OUT([Güvenilirlik damgalı brifing])

```

