
# Frontend Dockerfile
FROM node:22-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

# Build args
ARG API_URL
ARG WS_URL
ENV VITE_API_URL=$API_URL
ENV VITE_WS_URL=$WS_URL

RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Copy custom nginx config if we needed to handle routing, but for / it's fine.
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
