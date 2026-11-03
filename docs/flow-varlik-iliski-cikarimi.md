# Akış Diyagramı: Varlık-İlişki Çıkarımı ve Neo4j'ye Yazma

**İlgili ister:** REQ-02 Dinamik Ağ Kurulumu
**İlgili bileşen:** Bilgi Çıkarım Ajanı (Katman 2), Neo4j, PostgreSQL, Redis

Araştırma Ajanı'nın çektiği ham metin burada düğüm ve ilişkilere dönüştürülür. Diyagram mutlu yolu ve hata dallarını birlikte gösterir.

```mermaid
flowchart TD
    A(["Ham metin + source_id<br/>Araştırma Ajanı'ndan"]) --> B{"Metin yeterli<br/>uzunlukta mı?"}
    B -->|Hayır| B1["Kaynağı 'içerik yetersiz'<br/>olarak işaretle ve logla"]
    B1 --> END1(["Bitir: çıkarım yok"])
    B -->|Evet| C["Metni temizle ve<br/>chunk'lara böl"]

    C --> D["Sıradaki chunk'ı al"]
    D --> E["Yerel LLM ile varlık ve<br/>ilişki çıkar: JSON çıktı"]
    E --> F{"Çıktı geçerli JSON ve<br/>şemaya uygun mu?"}

    F -->|Hayır| G{"Yeniden deneme<br/>sayısı 2'den az mı?"}
    G -->|Evet| G1["Hata mesajıyla<br/>düzeltme istemi hazırla"]
    G1 --> E
    G -->|Hayır| H{"API modeli<br/>denendi mi?"}
    H -->|Hayır| H1["Chunk'ı API modeline<br/>yükselt"]
    H1 --> E
    H -->|Evet| J["Chunk'ı 'çıkarım başarısız'<br/>olarak işaretle ve logla"]
    J --> NEXT

    F -->|Evet| K["Her öğe için kanıt cümlesi<br/>chunk metninde geçiyor mu? kontrol et"]
    K --> L{"Kanıt metinde<br/>bulundu mu?"}
    L -->|Hayır| M["Öğeyi at, 'dayanaksız çıkarım'<br/>olarak logla"]
    M --> NEXT
    L -->|Evet| N["Varlık eşleştirme:<br/>ad normalizasyonu ve<br/>Neo4j'de benzer düğüm ara"]

    N --> O{"Benzerlik skoru?"}
    O -->|Yüksek| P["Mevcut düğümle birleştir,<br/>yeni adı alias olarak ekle"]
    O -->|Belirsiz| Q["Yeni düğüm oluştur,<br/>needs_review işaretle"]
    O -->|Düşük| R["Yeni düğüm oluştur"]

    P --> S["Neo4j'ye MERGE ile yaz,<br/>source_ids alanına source_id ekle"]
    Q --> S
    R --> S

    S --> T{"Yazma<br/>başarılı mı?"}
    T -->|Hayır| U{"Yeniden deneme<br/>sayısı 3'ten az mı?"}
    U -->|Evet| U1["Bekle: üstel geri çekilme"]
    U1 --> S
    U -->|Hayır| U2["Öğeyi Redis hata kuyruğuna<br/>koy ve logla"]
    U2 --> NEXT
    T -->|Evet| V["PostgreSQL'de chunk'ı<br/>'işlendi' olarak işaretle"]
    V --> NEXT

    NEXT{"Başka chunk<br/>var mı?"}
    NEXT -->|Evet| D
    NEXT -->|Hayır| W["Orkestratöre özet gönder:<br/>yeni düğüm ve ilişki sayısı,<br/>başarısız chunk sayısı"]
    W --> END2(["Bitir: Orkestratör<br/>bilgi kazancını hesaplar"])
```

## Hata dalları

| Hata durumu | Tespit | Sistem davranışı | Loglanan olay |
|-------------|--------|------------------|---------------|
| Metin boş veya çok kısa | Karakter sayısı eşiğin altında | Kaynak işaretlenir, çıkarım atlanır | `extraction_skipped_low_content` |
| LLM geçersiz JSON döndürdü | JSON ayrıştırma veya şema doğrulama hatası | Hata mesajıyla en fazla 2 kez tekrar denenir | `extraction_retry` |
| Yerel model başarısız | 2 yeniden deneme sonrası hâlâ geçersiz | Chunk bir kez API modeline yükseltilir | `extraction_escalated` |
| API modeli de başarısız | Yükseltme sonrası hâlâ geçersiz | Chunk "çıkarım başarısız" olur, akış sonraki chunk ile devam eder | `extraction_failed` |
| LLM metinde olmayan bilgi üretti | Kanıt cümlesi chunk içinde bulunamıyor | Öğe atılır (REQ-06 ile uyumlu) | `extraction_ungrounded` |
| Belirsiz varlık eşleşmesi | Benzerlik skoru iki eşik arasında | Yeni düğüm açılır, `needs_review` işaretlenir | `entity_ambiguous` |
| Neo4j yazma hatası | Bağlantı veya zaman aşımı | En fazla 3 kez üstel geri çekilmeyle denenir, sonra Redis hata kuyruğuna alınır | `graph_write_retry`, `graph_write_dead_letter` |

## Tasarım notları

- **Kanıt zorunluluğu:** LLM her varlık ve ilişki için kaynak cümleyi (`evidence`) de döndürür. Bu cümle chunk metninde yoksa öğe atılır. Böylece uydurma bilgi grafiğe girmeden engellenir.
- **MERGE kullanımı:** Aynı varlık tekrar geldiğinde kopya düğüm oluşmaz, yalnızca `source_ids` listesine yeni kaynak eklenir.
- **Hataya dayanıklılık:** Bir chunk'ın başarısız olması tüm araştırmayı durdurmaz. Başarısız chunk sayısı Orkestratör'e raporlanır.
- **Eşikler:** Benzerlik eşikleri ve yeniden deneme sayıları ayarlanabilir olarak tasarlanır, ilk değerler baseline çalışmasında belirlenir (Hafta 3).
