FROM python:3.11-slim

# Install Node + npm
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

# Install Python USD packages
RUN pip install usd-core trimesh numpy

WORKDIR /app

# Copy Node files
COPY package.json server.js convert.py ./

# Install Node dependencies
RUN npm install

EXPOSE 3000

CMD ["node", "server.js"]
