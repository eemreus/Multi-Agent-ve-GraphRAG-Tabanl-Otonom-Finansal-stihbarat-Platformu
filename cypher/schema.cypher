// docs/06-neo4j-graf-semasi.md ile aynı kısıt ve indeksler (tekrar çalıştırmak güvenlidir)
CREATE CONSTRAINT company_id IF NOT EXISTS FOR (n:Company) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (n:Person) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT event_id IF NOT EXISTS FOR (n:Event) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT location_id IF NOT EXISTS FOR (n:Location) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT metric_id IF NOT EXISTS FOR (n:Metric) REQUIRE n.id IS UNIQUE;
CREATE INDEX company_norm IF NOT EXISTS FOR (n:Company) ON (n.normalized_name);
CREATE INDEX person_norm IF NOT EXISTS FOR (n:Person) ON (n.normalized_name);
CREATE INDEX company_ticker IF NOT EXISTS FOR (n:Company) ON (n.ticker);
CREATE INDEX event_date IF NOT EXISTS FOR (n:Event) ON (n.date);
CREATE FULLTEXT INDEX entity_names IF NOT EXISTS FOR (n:Company|Person) ON EACH [n.name, n.aliases];
