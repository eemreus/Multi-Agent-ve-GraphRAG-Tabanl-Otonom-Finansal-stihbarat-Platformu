\# Akış Diyagramları



\## Akış 1: Uçtan uca sorgu → brifing (ReAct + durma ölçütü)



Kullanıcı sorgusu alt sorulara bölünür, araştırma döngüsü iki durma ölçütünden biri tetiklenene kadar sürer. İlgili ister: REQ-01, REQ-03, REQ-04.



```mermaid

flowchart TD

&#x20;   U(\[Kullanıcı sorgusu]) --> API\[FastAPI Gateway<br/>kimlik doğrulama]

&#x20;   API --> ORC1\[Orkestratör Ajan<br/>sorguyu alt sorulara böler]

&#x20;   ORC1 --> BUDGET{Döngü ve token<br/>bütçesi doldu mu?}



&#x20;   BUDGET -- Hayır --> RES\[Araştırma Ajanı<br/>SearXNG ile ara,<br/>Trafilatura ile metni çek]

&#x20;   RES --> EXTR\[Bilgi Çıkarım Ajanı<br/>varlık ve ilişki çıkarır]

&#x20;   EXTR --> NEO\[(Neo4j<br/>Bilgi Grafiği)]

&#x20;   NEO --> GAIN{Bilgi kazancı<br/>eşiğin altında mı?}



&#x20;   GAIN -- Hayır, bilgi eksik --> ORC2\[Orkestratör<br/>yeni alt sorgu üretir]

&#x20;   ORC2 --> BUDGET



&#x20;   GAIN -- Evet, yeterli --> VER

&#x20;   BUDGET -- Evet, bütçe bitti --> VER\[Doğrulama Ajanı<br/>çapraz doğrulama,<br/>güven puanı]



&#x20;   VER --> REP\[Raporlama Ajanı<br/>kaynak bağlantılı brifing]

&#x20;   REP --> OUT(\[Güvenilirlik damgalı brifing])

```

