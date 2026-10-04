FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=Asia/Tashkent
WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY init_db.py create_user.py ./
COPY deploy/entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh && useradd -r -u 10001 appuser && chown -R appuser /srv
USER appuser

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
