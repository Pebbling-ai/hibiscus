FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install uv
# Copy project files
COPY . .

# Install Python dependencies with uv
RUN uv pip install -e .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
