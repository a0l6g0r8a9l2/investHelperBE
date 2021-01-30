FROM python:3.7
COPY . /app/bot
WORKDIR /app/bot
RUN pip install -U setuptools pip
RUN pip install -r requirements.txt
ENV PYTHONPATH "${PYTHONPATH}/app"
CMD ["main.py"]
ENTRYPOINT ["python3"]