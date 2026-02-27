FROM ubuntu:22.04

RUN apt-get update && apt-get install -y curl xz-utils libxi6 libxxf86vm1 libxrender1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -L https://mirror.clarkson.edu/blender/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz \
    | tar xJ -C /opt/ \
    && ln -s /opt/blender-4.0.2-linux-x64/blender /usr/local/bin/blender

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

WORKDIR /app
COPY package.json server.js convert.py ./
RUN npm install

EXPOSE 3000
CMD ["node", "server.js"]
