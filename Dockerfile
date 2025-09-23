FROM python:3.13-slim

# Set working directory inside container to collector
WORKDIR /app/collector

# Copy requirements first
COPY collector/requirements.txt /app/collector/requirements.txt
RUN pip install --no-cache-dir -r /app/collector/requirements.txt

# Copy entire collector folder
COPY collector /app/collector

# Expose Flask port
EXPOSE 5000

# Ensure Python can see 'app' package
ENV PYTHONPATH=/app/collector

# Run wsgi.py directly
CMD ["python", "wsgi.py"]
