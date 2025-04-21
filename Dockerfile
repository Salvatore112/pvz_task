FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install -e .

EXPOSE 8080
EXPOSE 9000

CMD ["uvicorn", "myapp.app:app", "--host", "0.0.0.0", "--port", "8080"]