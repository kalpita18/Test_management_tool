FROM python:3.10-slim

WORKDIR /app


# copy everything from backend context to /app (respects .dockerignore)
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]