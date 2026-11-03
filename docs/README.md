# Dokümantasyon İndeksi

Multi-Agent ve GraphRAG Tabanlı Otonom Finansal İstihbarat Platformu

Ekip: Muhammed Emre ULAŞ (230291028, GitHub: @eemreus), Ayşe Sıla İNCİ (230291023, GitHub: @aysesilainci)

## Hafta 1 – Diyagramlar

| # | Belge | Sorumlu | Durum |
|---|-------|---------|-------|
| 1 | [Use Case Diyagramı](01-use-case.md) | Emre | Tamamlandı |
| 2 | [Sistem Mimarisi](02-architecture.md) | Emre | Tamamlandı |
| 3 | [Akış Diyagramları: Akış 1 (uçtan uca sorgu), Akış 2 (web tarama), Akış 4 (atıf doğrulama)](03-flows.md) | Sıla | Tamamlandı |
| 4 | [Akış 3: Varlık-ilişki çıkarımı ve Neo4j'ye yazma](flow-varlik-iliski-cikarimi.md) | Emre | Tamamlandı |
| 5 | [AI Pipeline Diyagramı](04-ai-pipeline.md) | Sıla | Tamamlandı |
| 6 | İsterlerin GitHub Issues'a aktarımı ([#2](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/2) – [#7](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/7)) | Emre: REQ-01, 02, 03 / Sıla: REQ-04, 05, 06 | Tamamlandı |

Akış diyagramlarında hata dalları gösterilmiştir (bot engeli, zaman aşımı, geçersiz LLM çıktısı, uydurma atıf vb.).

## Hafta 2 – Mockup + Veritabanı

| # | Belge | Sorumlu | Durum |
|---|-------|---------|-------|
| 1 | [Figma tıklanabilir prototip, 8 ekran](09-mockup.md), [issue #14](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/14) | Emre | Tamamlandı |
| 2 | [ER Diyagramı (PostgreSQL)](05-er-diyagrami.md) | Emre | Tamamlandı |
| 3 | [Neo4j Graf Şeması](06-neo4j-graf-semasi.md) | Emre | Tamamlandı |
| 4 | [Veri Sözlüğü](07-veri-sozlugu.md) | Emre + Sıla | Tamamlandı |
| 5 | [Teknoloji Yığını Tablosu](08-teknoloji-yigini.md) | Emre + Sıla | Tamamlandı (öneri, açık kararlar Hafta 3'te netleşir) |
| 6 | [5 dk sınıf sunumu](sunum/ParaGoz-Hafta1-2-Sunum.pdf) ([PowerPoint](sunum/ParaGoz-Hafta1-2-Sunum.pptx), konuşma notları dosyanın içinde) | Emre + Sıla | Tamamlandı |

## İsterler ve belgeler

| İster | GitHub Issue | İlgili belgeler |
|-------|--------------|-----------------|
| REQ-01 Otonom Tarama | [#2](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/2) | [Use case](01-use-case.md), [Mimari](02-architecture.md), [Akış 1 ve 2](03-flows.md), [AI pipeline](04-ai-pipeline.md) |
| REQ-02 Dinamik Ağ Kurulumu | [#3](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/3) | [Akış 3](flow-varlik-iliski-cikarimi.md), [Neo4j şeması](06-neo4j-graf-semasi.md) |
| REQ-03 Şeffaf Kaynak Gösterimi | [#4](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/4) | [ER diyagramı](05-er-diyagrami.md), [Veri sözlüğü](07-veri-sozlugu.md), [Mockup](09-mockup.md) |
| REQ-04 Güvenilirlik Damgası | [#5](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/5) | [AI pipeline](04-ai-pipeline.md), [Veri sözlüğü](07-veri-sozlugu.md) |
| REQ-05 Düşük Gecikmeli API Servisi | [#6](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/6) | [Mimari](02-architecture.md), [Teknoloji yığını](08-teknoloji-yigini.md) |
| REQ-06 Kaynak Denetimi ve Güvenlik | [#7](https://github.com/eemreus/Multi-Agent-ve-GraphRAG-Tabanl-Otonom-Finansal-stihbarat-Platformu/issues/7) | [Akış 4 (atıf doğrulama)](03-flows.md), [Veri sözlüğü](07-veri-sozlugu.md) |

Detaylı iş bölümü: [TASK_DISTRIBUTION.md](TASK_DISTRIBUTION.md)

## Çalışma kuralları

- Tüm dokümanlar `docs/` klasöründe tutulur.
- Diyagramlar Mermaid ile yazılır, GitHub üzerinde doğrudan görüntülenir. Use case diyagramı okunabilirlik için Graphviz ile üretilmiştir (`docs/img/`).
- Her kişi kendi branch'inde çalışır (`feat/emre-...`, `feat/sila-...`), Pull Request ile `main`'e birleştirir. Böylece iki kişinin commit'i de görünür.
- Commit mesajı formatı: `docs: use case diyagramı eklendi`
