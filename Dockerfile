FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install only runtime dependencies.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        "python-telegram-bot[job-queue]>=22.5" \
        "python-dotenv>=1.0"

# Copy only the application code.
COPY onani_memo_chan ./onani_memo_chan

CMD ["python", "-m", "onani_memo_chan"]
