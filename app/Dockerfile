FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7
RUN pip install --upgrade pip
COPY . /app/app
WORKDIR /app/app
RUN pip install -r requirements.txt
# RUN chmod +x ./tests/startTests.sh
# RUN ./tests/startTests.sh