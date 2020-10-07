FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7
# Базовый образ, всегда 1й строкой
RUN pip install --upgrade pip
# Upgrade pip
# RUN mkdir -p ./app
COPY ./app /app/app
WORKDIR /app/app
RUN pip install -r requirements.txt
# RUN startTests.sh
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]