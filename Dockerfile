FROM python:3.12-slim

WORKDIR /srv

COPY requirements.txt .
# Generous timeout/retries: compose builds api, worker and warmup in parallel
# alongside web's npm ci, and on a slow link pip's 15s default times out
# fetching the index ("from versions: none").
RUN pip install --no-cache-dir --timeout 120 --retries 10 -r requirements.txt

COPY app ./app
# categories.json is read by worker.py at a fixed path (BASE_DIR/categories.json),
# not via an env var — without it the classify loop fails every cycle.
COPY subcategory.txt schemaextractevent.txt data.json.txt categories.json ./

ENV PYTHONUNBUFFERED=1

EXPOSE 9911

CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "9911"]
