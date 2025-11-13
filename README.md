# 🎤 Voice Speaker Recognition System

Система распознавания и сравнения голосов спикеров из видео с YouTube с использованием глубокого обучения.

## 📋 Описание

Это веб-приложение позволяет:
- Сравнивать голоса двух спикеров из разных видео
- Определять вероятность того, что это один и тот же человек
- Создавать голосовые профили из видео
- Обрабатывать целые плейлисты YouTube
- Использовать субтитры для улучшения точности распознавания
- Фильтровать шумы и выделять чистую речь

## 🏗️ Архитектура

### Компоненты Backend:

1. **YouTube Downloader** (`youtube_downloader.py`)
   - Загрузка видео с YouTube
   - Поддержка плейлистов и каналов
   - Получение метаданных видео

2. **Audio Processor** (`audio_processor.py`)
   - Извлечение аудио из видео
   - Улучшение качества звука
   - Шумоподавление и нормализация

3. **Voice Analyzer** (`voice_analyzer.py`)
   - Детектирование голосовой активности (VAD)
   - Оценка качества аудио
   - Выделение сегментов речи

4. **Speaker Recognition** (`speaker_recognition.py`)
   - Создание голосовых отпечатков (embeddings)
   - Сравнение голосов
   - Расчет вероятности совпадения

5. **Transcript Analyzer** (`transcript_analyzer.py`)
   - Получение субтитров с YouTube
   - Определение временных меток говорящего
   - Фильтрация по целевому спикеру

### Frontend:
- Современный веб-интерфейс
- Три режима работы:
  - Сравнение двух спикеров
  - Анализ одного спикера
  - Обработка плейлистов
- Отображение прогресса в реальном времени
- Детальные метрики качества

## 🚀 Установка

### Требования

- Python 3.8+
- FFmpeg
- CUDA (опционально, для GPU ускорения)

### 1. Клонировать репозиторий

```bash
git clone <repository-url>
cd voice_compare
```

### 2. Создать виртуальное окружение

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Установить FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Скачать с [ffmpeg.org](https://ffmpeg.org/download.html)

## 📦 Использование

### Запуск сервера

```bash
cd backend
python app.py
```

Сервер запустится на `http://localhost:8000`

### Открыть веб-интерфейс

Откройте в браузере: `http://localhost:8000/static/index.html`

### Использование API

#### 1. Сравнить два спикера

```bash
curl -X POST http://localhost:8000/api/compare-speakers \
  -H "Content-Type: application/json" \
  -d '{
    "video1_urls": ["https://www.youtube.com/watch?v=VIDEO1"],
    "video2_urls": ["https://www.youtube.com/watch?v=VIDEO2"],
    "use_transcripts": true
  }'
```

#### 2. Проанализировать голос

```bash
curl -X POST http://localhost:8000/api/download-video \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://www.youtube.com/watch?v=VIDEO"],
    "target_speaker": "John Doe",
    "use_transcripts": true
  }'
```

#### 3. Обработать плейлист

```bash
curl -X POST http://localhost:8000/api/download-playlist \
  -H "Content-Type: application/json" \
  -d '{
    "playlist_url": "https://www.youtube.com/playlist?list=PLAYLIST_ID",
    "use_transcripts": true
  }'
```

#### 4. Проверить статус задачи

```bash
curl http://localhost:8000/api/job/{job_id}
```

## 🎯 Примеры использования

### Пример 1: Сравнение голосов

Загрузите видео двух спикеров и получите оценку вероятности того, что это один и тот же человек:

```python
import requests

response = requests.post('http://localhost:8000/api/compare-speakers', json={
    'video1_urls': [
        'https://www.youtube.com/watch?v=video1',
        'https://www.youtube.com/watch?v=video2'
    ],
    'video2_urls': [
        'https://www.youtube.com/watch?v=video3',
        'https://www.youtube.com/watch?v=video4'
    ],
    'target_speaker1': 'Speaker A',
    'target_speaker2': 'Speaker B',
    'use_transcripts': True
})

job_id = response.json()['job_id']

# Проверяем статус
status = requests.get(f'http://localhost:8000/api/job/{job_id}')
result = status.json()

print(f"Similarity: {result['result']['similarity_score']}")
print(f"Interpretation: {result['result']['interpretation']}")
```

### Пример 2: Создание голосового профиля

```python
response = requests.post('http://localhost:8000/api/download-video', json={
    'urls': [
        'https://www.youtube.com/watch?v=video1',
        'https://www.youtube.com/watch?v=video2',
        'https://www.youtube.com/watch?v=video3'
    ],
    'target_speaker': 'John Doe',
    'use_transcripts': True
})
```

## 📊 Интерпретация результатов

### Коэффициент схожести (Similarity Score)

- **90-100%**: Очень высокая вероятность - скорее всего один и тот же человек
- **75-90%**: Высокая вероятность - вероятно один и тот же человек
- **60-75%**: Средняя вероятность - возможно один и тот же человек
- **40-60%**: Низкая вероятность - скорее всего разные люди
- **0-40%**: Очень низкая вероятность - почти наверняка разные люди

### Метрики качества

- **Quality Level**: Общая оценка качества аудио (excellent/good/fair/poor)
- **Speech Duration**: Длительность обнаруженной речи
- **Speech Ratio**: Отношение речи к общей длительности
- **Average Quality Score**: Средний балл качества
- **Sufficient Data**: Достаточно ли данных для точного анализа

## 🔧 Технологии

### Backend:
- **FastAPI** - веб-фреймворк
- **yt-dlp** - загрузка с YouTube
- **FFmpeg** - обработка аудио/видео
- **librosa** - анализ аудио
- **SpeechBrain** - распознавание спикера
- **PyTorch** - глубокое обучение
- **webrtcvad** - детектирование голоса
- **youtube-transcript-api** - получение субтитров

### Frontend:
- HTML5
- CSS3 (с градиентами и анимациями)
- Vanilla JavaScript
- Fetch API для асинхронных запросов

### ML Модели:
- **ECAPA-TDNN** (SpeechBrain) - для извлечения голосовых embeddings
- **VoxCeleb** - предобученная модель на большом датасете голосов

## 📁 Структура проекта

```
voice_compare/
├── backend/
│   ├── app.py                    # Главное FastAPI приложение
│   ├── youtube_downloader.py     # Загрузка с YouTube
│   ├── audio_processor.py        # Обработка аудио
│   ├── voice_analyzer.py         # Анализ голоса (VAD)
│   ├── speaker_recognition.py    # Распознавание спикера
│   └── transcript_analyzer.py    # Анализ субтитров
├── static/
│   ├── index.html               # Веб-интерфейс
│   ├── styles.css               # Стили
│   └── app.js                   # JavaScript логика
├── data/
│   ├── videos/                  # Загруженные видео
│   ├── audio/                   # Извлеченное аудио
│   └── models/                  # ML модели
├── requirements.txt             # Python зависимости
└── README.md                    # Документация
```

## 🛠️ Разработка

### Запуск в режиме разработки

```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Логирование

Все компоненты используют Python logging. Логи выводятся в консоль.

### Тестирование

```bash
# Тест API
curl http://localhost:8000/health

# Должен вернуть: {"status": "healthy"}
```

## 🐛 Решение проблем

### FFmpeg не найден
```bash
# Проверить установку
ffmpeg -version

# Установить если нужно
sudo apt-get install ffmpeg  # Ubuntu
brew install ffmpeg          # macOS
```

### Ошибка загрузки с YouTube
- Убедитесь что видео публичное
- Проверьте доступность YouTube
- Обновите yt-dlp: `pip install -U yt-dlp`

### Медленная обработка
- Используйте GPU если доступно (установите torch с CUDA)
- Уменьшите количество видео
- Используйте более короткие видео

### Недостаточно памяти
- Обрабатывайте видео по одному
- Уменьшите размер батча
- Освободите память: перезапустите сервер

## 📝 Лицензия

MIT License

## 👥 Авторы

Разработано с использованием современных технологий машинного обучения и обработки аудио.

## 🤝 Вклад

Pull requests приветствуются! Для крупных изменений сначала откройте issue для обсуждения.

## 📧 Контакты

Для вопросов и предложений создайте issue в репозитории.

---

**Примечание**: Эта система предназначена для легального использования. Всегда получайте разрешение перед анализом чужих голосов.
