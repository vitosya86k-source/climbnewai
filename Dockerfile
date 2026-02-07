FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для OpenCV и MediaPipe
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаем необходимые директории
RUN mkdir -p data/temp data/exports data/boldering_vector

# Запуск
CMD ["python", "app/main.py"]


