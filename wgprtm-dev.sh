#!/usr/bin/env bash

# sed routes with extra "/"
sed -i.bak 's/@router\.post("\/",/@router.post("",/g; s/@router\.get("\/",/@router.get("",/g' ./backend/app/api/api_v1/chat.py
sed -i.bak 's/@router\.post("\/",/@router.post("",/g; s/@router\.get("\/",/@router.get("",/g' ./backend/app/api/api_v1/api_keys.py

COMPOSE_HTTP_TIMEOUT=180 docker compose \
  -f docker-compose-wgprtm.dev.yml \
  "$@"
