FROM python:3.11-slim

WORKDIR /app

# Salin file-file konfigurasi dan dependensi terlebih dahulu
COPY requirements.txt .
COPY config.json .

# Install semua dependensi Python
RUN pip install --no-cache-dir -r requirements.txt

# Salin sisa kode sumber aplikasi
COPY ./app ./app
COPY main.py .

# Jalankan bot saat kontainer dimulai
CMD ["python3", "main.py"]
