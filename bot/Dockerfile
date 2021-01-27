FROM python:3
COPY . /app/bot
WORKDIR /app/bot
RUN pip install -r requirements.txt
ENV PYTHONPATH "${PYTHONPATH}/app"
CMD ["main.py"]
ENTRYPOINT ["python3"]