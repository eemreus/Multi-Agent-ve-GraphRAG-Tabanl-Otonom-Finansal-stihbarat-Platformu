# Görev Dağılımı

## Genel prensip

- Her görev tek bir kişiye atanır, diğer kişi gözden geçirir (PR review).
- Her iki kişi de her hafta en az birkaç anlamlı commit atar.
- Branch isimleri: `feat/emre-<konu>`, `feat/sila-<konu>`

## Hafta 1: Diyagramlar

| Görev | Sorumlu | Gözden geçiren | Branch |
|-------|---------|----------------|--------|
| Use case diyagramı | Emre | Sıla | `feat/emre-usecase` |
| Sistem mimarisi diyagramı | Emre | Sıla | `feat/emre-architecture` |
| Akış 1: Uçtan uca sorgu → brifing (ReAct + durma ölçütü) | Sıla | Emre | `feat/sila-flows` |
| Akış 2: Web tarama ve içerik çekme (bot engeli, fallback) | Sıla | Emre | `feat/sila-flows` |
| Akış 3: Varlık-ilişki çıkarımı ve Neo4j'ye yazma | Emre | Sıla | `feat/emre-flows` |
| Akış 4 (bonus): Atıf doğrulama | Sıla | Emre | `feat/sila-flows` |
| AI pipeline diyagramı | Sıla | Emre | `feat/sila-pipeline` |
| GitHub Issues: REQ-01, 02, 03 | Emre | Sıla | - |
| GitHub Issues: REQ-04, 05, 06 | Sıla | Emre | - |

## Hafta 2: Mockup + Veritabanı

| Görev | Sorumlu | Gözden geçiren |
|-------|---------|----------------|
| Figma prototipi (en az 6 ekran) | Sıla | Emre |
| ER diyagramı (PostgreSQL) | Emre | Sıla |
| Neo4j graf şeması | Emre | Sıla |
| Veri sözlüğü | Emre + Sıla | Karşılıklı |
| Teknoloji yığını tablosu | Emre + Sıla | Karşılıklı |
| 5 dk sunum hazırlığı | Emre + Sıla | - |

## Genel not

Bu dağılım bir başlangıç önerisidir, isterseniz değiştirilebilir. Önemli olan haftalar boyunca yükün dengeli kalması ve her iki kişinin commit geçmişinin repoda görünmesidir.
