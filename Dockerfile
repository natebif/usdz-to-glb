FROM python:3.11-slim

# Install node (for server.js) and pip packages
RUN apt-get update && apt-get install -y nodejs npm && \
    pip install --no-cache-dir usd-core trimesh numpy && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY package.json server.js convert.py ./

# Install Node dependencies
RUN npm install

EXPOSE 3000

CMD ["node", "server.js"]
