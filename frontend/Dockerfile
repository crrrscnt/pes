FROM node:18-slim

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Настройки npm для стабильной работы в Docker
RUN npm config set fetch-retry-maxtimeout 120000 \
 && npm config set fetch-retry-mintimeout 20000 \
 && npm config set fetch-timeout 120000 \
 && npm config set maxsockets 1

# Install dependencies
# RUN npm ci --only=production
RUN npm ci # --omit=dev

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 5173

# Command to run the application
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
