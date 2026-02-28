FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates xz-utils \
    libtbb2 libpng-dev libjpeg-dev \
    libxi6 libxxf86vm1 libxfixes3 libgl1-mesa-glx \
    libxkbcommon0 libsm6 libice6 libx11-6 libxext6 libxrender1 \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*


RUN curl -L https://mirror.clarkson.edu/blender/release/Blender4.1/blender-4.1.1-linux-x64.tar.xz \
    -o /tmp/blender.tar.xz \
    && tar xf /tmp/blender.tar.xz -C /opt/ \
    && rm /tmp/blender.tar.xz

ENV PATH="/opt/blender-4.1.1-linux-x64:${PATH}"
ENV LD_LIBRARY_PATH="/opt/blender-4.1.1-linux-x64/lib:${LD_LIBRARY_PATH}"


WORKDIR /app
COPY package.json ./
RUN npm install
COPY server.js convert.py ./

EXPOSE 3000
CMD ["node", "server.js"]

