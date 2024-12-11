# Base image
FROM python:3.13-slim

# Set the working directory
WORKDIR /my_app

# Copy files
COPY . /my_app

# Install dependencies
RUN pip install --no-cache-dir -r /my_app/requirements.txt

# Expose ports
EXPOSE 3000
EXPOSE 5000

# Run the app
CMD ["python", "main.py"]