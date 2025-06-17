FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt config.json .env ./

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app
COPY main.py .

CMD ["python3", "main.py"]
