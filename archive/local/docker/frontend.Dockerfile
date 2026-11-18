FROM node:22-alpine

WORKDIR /app

COPY app/frontend/package.json app/frontend/package-lock.json* /app/
RUN npm ci
COPY app/frontend /app

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
