FROM python:3.12-slim

# Set Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files first
COPY pyproject.toml README.md ./
COPY uv.lock ./

# Install dependencies and uvicorn explicitly
RUN uv pip install -r uv.lock && \
    pip install uvicorn

# Copy application code
COPY . .

# Create a non-root user
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app

# Use non-root user
USER appuser

EXPOSE 8000

# Run with python -m to ensure correct paths
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]