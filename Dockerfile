FROM ubuntu:22.04

# Install Blender dependencies + Node 20 prerequisites
RUN apt-get update && apt-get install -y \
    curl xz-utils libxi6 libxxf86vm1 libxrender1 libgl1 \
    libxkbcommon0 libxrandr2 libxcursor1 libxinerama1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Download and extract Blender 4.0.2, symlink to /usr/local/bin
RUN curl -L https://mirror.clarkson.edu/blender/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz \
    | tar xJ -C /opt/ \
    && ln -s /opt/blender-4.0.2-linux-x64/blender /usr/local/bin/blender

# Install Node 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Set working directory
WORKDIR /app

# Copy app files and install Node dependencies
COPY package.json server.js convert.py ./
RUN npm install

# Expose port
EXPOSE 3000

# Start server
CMD ["node", "server.js"]