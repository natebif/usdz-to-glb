FROM ubuntu:22.04

# Install system deps
RUN apt-get update && apt-get install -y \
    curl \
    blender \
    && rm -rf /var/lib/apt/lists/*

# Install Node 20 (official)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

WORKDIR /app

COPY package.json server.js convert.py ./

RUN npm install

EXPOSE 3000

CMD ["node", "server.js"]