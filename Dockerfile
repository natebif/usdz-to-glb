FROM python:3.11-slim
RUN pip install usd-core trimesh numpy
WORKDIR /app
COPY package.json server.js convert.py ./
RUN apt-get update && apt-get install -y nodejs npm && npm install
EXPOSE 3000
CMD ["node", "server.js"]

