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

# Initialize a dummy git repo so MANDATE doesn't crash if it tries to check diffs
RUN git config --global init.defaultBranch main && \
    git config --global user.email "bot@mandate.ai" && \
    git config --global user.name "MANDATE Bot" && \
    git init && \
    git add . && \
    git commit -m "Initial commit for Zop.dev deployment"

# Expose port 8080 for Zop.dev
EXPOSE 8080

# Command to run the FastAPI wrapper server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
