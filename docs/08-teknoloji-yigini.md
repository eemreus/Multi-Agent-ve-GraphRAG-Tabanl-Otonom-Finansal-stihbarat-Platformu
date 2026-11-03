# Teknoloji Yığını

Bu tablo **öneridir**. Hafta 3'teki baseline çalışmasında ve Hafta 4'teki backend iskeletinde denenip gerekirse güncellenir. Kararların nedenleri öneri formundaki risk planıyla (maliyet, bot engeli, gecikme) uyumludur.

## Seçilen teknolojiler

| Katman | Teknoloji | Neden seçildi | Alternatif |
|--------|-----------|---------------|------------|
| Programlama dili | Python 3 | LLM, NLP ve veri kütüphanelerinin çoğu Python'da, ekibin hızlı ilerlemesi için | - |
| Backend API | FastAPI + Pydantic | Otomatik Swagger/OpenAPI dokümantasyonu (REQ-05), asenkron çalışma, Pydantic ile LLM çıktısı şema doğrulaması | Flask, Django |
| Ajan orkestrasyonu | LangGraph | Döngülü (ReAct) ve dallanan akışları durum makinesi olarak ifade eder, durma ölçütü eklemek kolay | AutoGen (öneri formundaki referans), CrewAI |
| LLM (yönlendirici ve rapor) | Bir API modeli | Alt sorgu üretimi ve rapor yazımı gibi kalite gerektiren az sayıdaki çağrı için | Tamamen yerel model |
| LLM (çıkarım) | Ollama ile yerel model (Llama 3 ailesi) | Çok sayıda ucuz çağrıda token maliyetini ve API limitini düşürür (risk planı) | API modeli (yedek) |
| Embedding | Çok dilli bir sentence-transformers modeli | Türkçe metinlerde atıf-metin anlam benzerliği ve varlık eşleştirme için | API embedding servisi |
| Web arama | SearXNG (kendi sunucumuzda) | API anahtarı gerektirmez, birden çok arama motorunu birleştirir, sabit veri setine bağımlı değil | Serper, Brave API |
| Metin çekme | Trafilatura | Haber sayfalarından ana metni temiz çıkarır | newspaper3k, BeautifulSoup |
| Bot engeli yedeği | Proxy rotasyonu, KAP API, RSS | Cloudflare engeline karşı B planı (risk planı) | Playwright ile tarayıcı otomasyonu |
| Bilgi grafiği | Neo4j | Çok adımlı ilişki sorguları için doğal yapı, Cypher ile okunabilir sorgular (REQ-02) | Memgraph, ArangoDB |
| İlişkisel veritabanı | PostgreSQL | Kullanıcı, oturum, atıf, log kayıtları için; JSONB ve yüzdelik dilim sorguları (p@95) | SQLite (yalnızca geliştirme) |
| ORM ve migration | SQLAlchemy + Alembic | Hafta 4'te istenen migration yönetimi | Django ORM |
| Cache ve kuyruk | Redis | Sık sorulan graf ilişkileri için önbellek, hata kuyruğu, hafif görev kuyruğu | Memcached |
| Kimlik doğrulama | JWT (web) + API anahtarı (harici yazılım) | Basit ve FastAPI ile hazır entegre | OAuth2 sağlayıcıları |
| Frontend | React + TypeScript (Vite) | Bileşen yapısı canlı ilerleme ve rapor ekranları için uygun | Next.js, Vue |
| Arayüz stili | Tailwind CSS | Figma prototipinden hızlı arayüz çıkarmak için | MUI |
| Graf görselleştirme | Cytoscape.js | Bilgi grafiği gezgini ekranı için | react-force-graph, vis-network |
| Kapsayıcı | Docker + Docker Compose | Tüm servisler tek komutla kalkar, Hafta 8 deploy için (İP3) | Podman |
| Deploy | AWS veya GCP'de tek sanal makine, ya da yerel sunucu | İş planındaki tanım, küçük ölçekte yeterli | Render, Railway |
| İzleme | Yapılandırılmış loglar + Prometheus/Grafana veya Langfuse | Token, gecikme ve hata ölçümü (p@95) | Elasticsearch |
| Test | pytest, Locust veya k6 | Birim ve entegrasyon testleri, stres testi (Hafta 9) | - |
| CI | GitHub Actions | Repo zaten GitHub'da, otomatik test ve Mermaid kontrolü eklenebilir | - |
| Tasarım | Figma | Dersin istediği tıklanabilir prototip | - |
| Dokümantasyon | Mermaid + Markdown (`docs/`), Swagger | GitHub'da doğrudan görünür, sürüm kontrolünde tutulur | draw.io |

## Açık kararlar

Bunlar Hafta 3 baseline'ı sırasında deneyerek netleşir:

1. **Orkestrasyon:** LangGraph mı, AutoGen mi? Kriter: durma ölçütü ve hata dallarını ne kadar kolay ifade ettiği.
2. **Yerel model boyutu:** Bilgisayarlarımızdaki GPU/RAM'e bağlı. Türkçe varlık çıkarımında yeterli kalite veren en küçük model seçilir.
3. **API modeli seçimi:** Maliyet ve Türkçe kalite karşılaştırmasıyla belirlenir.
4. **Observability aracı:** Prometheus/Grafana mı, Langfuse mi? Kriter: kurulum kolaylığı ve ajan zinciri izleme.

## Katman - ister eşlemesi

| İster | Öne çıkan teknolojiler |
|-------|------------------------|
| REQ-01 Otonom Tarama | LangGraph, SearXNG, Trafilatura, Ollama / API modeli |
| REQ-02 Dinamik Ağ Kurulumu | Neo4j, Pydantic, Ollama |
| REQ-03 Şeffaf Kaynak Gösterimi | PostgreSQL, React |
| REQ-04 Güvenilirlik Damgası | PostgreSQL, embedding modeli, React |
| REQ-05 Düşük Gecikmeli API | FastAPI, Redis, Docker, Swagger |
| REQ-06 Kaynak Denetimi ve Güvenlik | Embedding modeli, PostgreSQL, pytest |
