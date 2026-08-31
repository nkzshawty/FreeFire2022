FROM ubuntu:24.04
COPY --from=node:20-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:20-slim /usr/local/bin/npm /usr/local/bin/npm
COPY --from=node:20-slim /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
WORKDIR /app
ENV NODE_ENV=production
ENV PATH=/usr/local/bin:/home/ubuntu/bin:/home/ubuntu/.local/bin:/home/ubuntu/.local/share/pnpm/bin:/home/ubuntu/.nvm/versions/node/v22.13.0/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
COPY node_modules ./node_modules
RUN mkdir -p node_modules/@auth && ln -s /app/shared node_modules/@auth/shared
COPY auth/ ./
CMD ["node", "connect-server/src/index.js"]
