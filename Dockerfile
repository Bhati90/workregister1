# Use official Python image
FROM python:3.12

# Set work directory
WORKDIR /app

# Install GDAL and other system dependencies
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

ARG DATABASE_URL

ENV DATABASE_URL=$DATABASE_URL
# Environment variable for GDAL
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Copy and install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port
EXPOSE 8000

# Run Django with Gunicorn
CMD  python manage.py makemigrations python manage.py migrate && gunicorn labour_crm.wsgi:application --bind 0.0.0.0:8000
