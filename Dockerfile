FROM ubuntu:22.04
RUN apt-get update && apt-get install -y blender nodejs npm && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package.json server.js convert.py ./
RUN npm install
EXPOSE 3000
CMD ["node", "server.js"]


