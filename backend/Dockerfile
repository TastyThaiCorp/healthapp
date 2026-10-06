# syntax=docker/dockerfile:1
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=secret,id=system_ca \
    if [ -f /run/secrets/system_ca ]; then export PIP_CERT=/run/secrets/system_ca; fi; pip install --no-cache-dir -r requirements.txt
COPY main.py accounts.py manage.py ./
COPY data ./data
RUN chmod -R a+rX /app && useradd --uid 10001 --create-home healthup && mkdir -p /data && chown healthup:healthup /data
USER 10001:10001
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --no-access-log"]
