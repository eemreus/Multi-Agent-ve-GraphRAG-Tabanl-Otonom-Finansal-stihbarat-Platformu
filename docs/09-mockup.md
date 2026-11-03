# Arayüz Mockup'ı (Figma Prototipi)

Ürün adı: **ParaGöz**. Koyu tema, 1440×900 masaüstü ekranları, 8 ekran, tıklanabilir.

**Figma dosyası:** https://www.figma.com/design/JhqPPsPylANSEqC1tVdCsr

Prototipi denemek için dosyayı aç, sağ üstteki Present (▶) düğmesine bas. Başlangıç noktası "ParaGöz: Giriş" ekranıdır.

## Ekranlar ve akış

| # | Ekran | Ne gösterir | Buradan nereye gidilir |
|---|-------|-------------|------------------------|
| 01 | Giriş | E-posta ve parola ile giriş (UC14) | Giriş yap → 02 |
| 02 | Panel | Son araştırmalar, token kullanımı, uydurma atıf oranı (UC7) | Yeni araştırma → 03, bir araştırma satırı → 05 |
| 03 | Yeni araştırma | Soru, token bütçesi, graf derinliği, kaynak türleri (UC1) | Araştırmayı başlat → 04 |
| 04 | Canlı ilerleme | Ajan adımları, token bütçesi, bilgi kazancı, taranan kaynaklar (UC2, UC9) | Brifingi görüntüle → 05 |
| 05 | Brifing raporu | Güven damgalı iddialar, çelişki ve düşük güven uyarıları (UC3, UC5, UC8) | Kaynak satırı → 06, Bilgi grafiğinde aç → 07 |
| 06 | Kaynak detayı | Kaynak künyesi, kaynak metindeki kanıt, atıf doğrulaması, güven puanı kırılımı (UC4) | Rapora dön → 05 |
| 07 | Bilgi grafiği | Düğüm türü, derinlik ve güven filtresi, seçili ilişkinin kaynağı (UC6) | Rapora dön → 05 |
| 08 | Ayarlar ve yönetim | Model ve bütçe, API anahtarları, kullanıcılar, telemetri (UC10, UC11, UC12, UC13) | Çıkış yap → 01 |

Sol menüdeki Panel, Yeni araştırma, Bilgi grafiği ve Ayarlar öğeleri her ekrandan çalışır.

## Ekran – ister eşlemesi

| İster | Ekranda nasıl görünür |
|-------|-----------------------|
| REQ-01 Otonom Tarama | 03 (soru, bütçe, durma ölçütü), 04 (ajan adımları, bot engeli ve proxy yedeği, bilgi kazancı) |
| REQ-02 Dinamik Ağ Kurulumu | 04 ("23 düğüm ve 31 ilişki yazıldı"), 07 (bilgi grafiği, derinlik 1–3) |
| REQ-03 Şeffaf Kaynak Gösterimi | 05 (her iddia altında kaynak çipi), 06 (URL, yayın ve erişim tarihi, kaynak metinden alıntı) |
| REQ-04 Güvenilirlik Damgası | 05 (Yüksek, Orta, Düşük, Çelişkili damgaları), 06 (dört etkenli puan kırılımı) |
| REQ-05 Düşük Gecikmeli API Servisi | 08 (API anahtarları, p@95 gecikme göstergesi) |
| REQ-06 Kaynak Denetimi ve Güvenlik | 02 ve 08 (uydurma atıf oranı), 06 (atıf benzerlik eşiği 0,75, geçti/kaldı) |

## Ekranlardaki alanların veri kaynağı

| Ekranda görünen | Veri sözlüğündeki karşılığı |
|-----------------|-----------------------------|
| Araştırma sorusu, durum, token sayısı | oturum kaydı ([veri sözlüğü](07-veri-sozlugu.md)) |
| İddia metni ve güven puanı | iddia kaydı |
| Kaynak URL, yayın tarihi, erişim tarihi, çekim yöntemi | kaynak kaydı |
| Atıf benzerliği (0,88) | atıf doğrulama kaydı |
| Düğüm ve ilişki (Selin Karaca, BOARD_MEMBER_OF) | [Neo4j şeması](06-neo4j-graf-semasi.md) |
| p@95 gecikme, token payı | log ve telemetri kaydı |

Ekranlardaki şirket, kişi ve haber siteleri (Atlas Enerji, Boreas Enerji, Selin Karaca, `.example` alanları) kurgusaldır.

## Tasarım kararları

- **Güven damgası:** Her iddianın yanında, renkle ve yazıyla belirtilen yuvarlak bir damga durur (yeşil Yüksek, sarı Orta, kırmızı Düşük, mor Çelişkili). Renk tek başına anlam taşımaz, damganın içinde puan ve etiket de yazar.
- **Kaynak çipi:** `[1] kap.org.tr · 2 Kas 2026` biçimi, REQ-03'teki "tıklanabilir kaynak ve erişim tarihi" şartını karşılar.
- **Uyarılar:** Çelişki ve düşük güven, raporun en üstünde ve ilgili iddianın altında ayrıca belirtilir.
- **Tek yazı tipi:** Inter.
