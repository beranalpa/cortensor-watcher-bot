version: "3.8"

services:
  watcher:
    build: .
    container_name: cortensor-watcher-bot
    restart: unless-stopped
    volumes:
      # Mount Docker socket untuk memanage kontainer lain
      - /var/run/docker.sock:/var/run/docker.sock
