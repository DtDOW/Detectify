# Use a Debian-based slim image (more predictable apt packages)
FROM python:3.10-slim-bullseye

# avoid interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
WORKDIR /app

# install system packages needed by opencv/mediapipe and pip build tools
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    wget \
    git \
    cmake \
    ffmpeg \
    libglib2.0-0 \
    libgl1-mesa-glx \
    libsm6 \
    libxext6 \
    libxrender1 \
    pkg-config \
 && rm -rf /var/lib/apt/lists/*

# copy requirements and install python deps
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy rest of project
COPY . /app

# expose port used by gunicorn
EXPOSE 5000

# run with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app", "--workers", "2", "--timeout", "120"]
#CMD ["python", "app.py"]


