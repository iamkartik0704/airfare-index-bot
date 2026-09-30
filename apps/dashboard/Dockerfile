FROM node:18-alpine
WORKDIR /app
COPY apps/dashboard/package*.json ./
# For this mock, just using npm install
RUN npm install || echo "No package.json, skipping"
COPY apps/dashboard/ .
CMD ["npm", "start"]
