# ParaGöz servis imajı: gateway ve graphrag-agent aynı imajı farklı komutla çalıştırır (docker-compose.yml).
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src ./src
COPY db ./db
COPY cypher ./cypher
COPY alembic.ini .
# data/ imaja girmez: compose ile salt okunur bağlanır (ham sayfa metinleri telifli olabilir).
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
