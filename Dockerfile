FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates xz-utils nodejs npm \
    libtbb2 libpng-dev libjpeg-dev \
    libxi6 libxxf86vm1 libxfixes3 libgl1-mesa-glx \
    libxkbcommon0 libsm6 libice6 libx11-6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -L https://mirror.clarkson.edu/blender/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz \
    | tar xJ -C /opt && ln -s /opt/blender-4.0.2-linux-x64/blender /usr/local/bin/blender

ENV LD_LIBRARY_PATH="/opt/blender-4.0.2-linux-x64/lib:${LD_LIBRARY_PATH}"

WORKDIR /app
COPY package.json ./
RUN npm install
COPY server.js convert.py ./

EXPOSE 3000
CMD ["node", "server.js"]

