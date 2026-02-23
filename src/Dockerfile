ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

ARG UID=10001
RUN adduser --disabled-password --gecos "" --uid ${UID} appuser

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install --requirement requirements.txt

USER appuser

COPY . .

EXPOSE 8000

CMD ["flask", "--app", "app", "run", "-h", "0.0.0.0", "-p", "8000"]
