FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home app

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip install --no-cache-dir --upgrade \
       "urllib3>=2.8.0" \
       "msgpack>=1.2.1" \
       "setuptools>=78.1.1"
    && python -m pip uninstall -y pip

COPY --chown=10001:10001 app ./app
COPY --chown=10001:10001 migrations ./migrations

USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]