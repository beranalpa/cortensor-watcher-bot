FROM python:3.11-slim

# BARIS TAMBAHAN: Install paket yang menyediakan perintah 'clear'
RUN apt-get update && apt-get install -y ncurses-bin && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Salin file-file konfigurasi, rahasia, dan dependensi
COPY requirements.txt config.json .env ./

# Install semua dependensi Python
RUN pip install --no-cache-dir -r requirements.txt

# Salin sisa kode sumber aplikasi
COPY ./app /app/app
COPY main.py .

# Jalankan bot saat kontainer dimulai
CMD ["python3", "main.py"]
