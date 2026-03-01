FROM python:3.10-slim

WORKDIR /project

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY data/ ./data/
COPY market_segmentation.py .
COPY preprocessing.py .
COPY scoring.py .
COPY zameen_karachi_flats_today.csv .
COPY zameen_karachi_flats_last_7_days.csv .
COPY zameen_market_segments.csv .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]