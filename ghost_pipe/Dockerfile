FROM node:20-alpine

# Install rclone and Doppler CLI
RUN apk update && apk add --no-cache rclone curl gnupg && \
    curl -Ls --tlsv1.2 --proto "=https" --retry 3 https://cli.doppler.com/install.sh | sh

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install --omit=dev

# Copy the rest of the application
COPY . .

# Set environment variables (can be overridden at runtime)
ENV NODE_ENV=production

# Run the engine (gracefully bypasses Doppler if token is missing so Cloud Run healthchecks pass)
CMD sh -c 'if [ -z "$DOPPLER_TOKEN" ]; then echo "Missing DOPPLER_TOKEN, booting without secrets"; node engine.js; else doppler run -- node engine.js; fi'
