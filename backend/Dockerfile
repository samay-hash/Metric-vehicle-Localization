FROM pytorch/pytorch:2.5.0-cuda12.4-cudnn9-runtime

WORKDIR /app

# Install system dependencies (needed for OpenCV/Ultralytics)
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
# Install other requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir transformers peft accelerate

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
