FROM python:3.11-slim

# Install dependencies
RUN pip install usd-core trimesh numpy

WORKDIR /app

# Copy files
COPY package.json server.js convert.py ./

# Install Node for server.js
RUN apt-get update && apt-get install -y nodejs npm && npm clean

# Install Node dependencies
RUN npm install

EXPOSE 3000

# Start server
CMD ["node", "server.js"]
