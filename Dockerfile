# Use the official Python base image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install git since MANDATE requires it to run reviews
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project code into the container
COPY . .

# Force Python to print output immediately (critical for Zop.dev logs)
ENV PYTHONUNBUFFERED=1



# Expose port 8000 for Zop.dev
EXPOSE 8000

# Command to run the FastAPI wrapper server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
