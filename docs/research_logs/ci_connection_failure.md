# Research Log - CI Connection Failure (Port 80)

## Problem Detail
The CI fails with `curl: (7) Failed to connect to localhost port 80 after 0 ms: Couldn't connect to server`.
The container status (`docker compose ps`) shows that `frontend` and `nginx` services are missing from the running containers list, while `backend`, `db`, `rabbitmq`, and others are running.

## Findings

### 1. Missing Services
In `docker-compose.yml`, the `nginx` service is responsible for mapping port 80:
```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
  depends_on:
    - frontend
    - backend
```
Since `nginx` and `frontend` are not running, port 80 is not exposed.

### 2. Volume Mount Conflict (Hypothesis)
In `docker-compose.yml`, the `frontend` service has the following volume mount:
```yaml
frontend:
  build: ./frontend
  volumes:
    - ./frontend:/app
    - /app/node_modules
```
The `frontend/Dockerfile` uses Next.js standalone output:
```dockerfile
# ... build steps ...
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
# ...
CMD ["node", "server.js"]
```
The build process places `server.js` and other artifacts in the container's `/app` directory. However, the volume mount `- ./frontend:/app` overrides this directory with the host's source code. Since `server.js` is a build artifact and not present in the host's `frontend/` source directory, the container fails to find `server.js` and exits immediately.

### 3. Nginx Dependency
Because `nginx` `depends_on: frontend`, if `frontend` fails to start correctly, `nginx` may also fail or be skipped depending on the exact startup timing and failure mode.

### 4. Backend Success
The `backend` service also has a volume mount `- ./backend:/app`, but its entrypoint is `./entrypoint.sh`, which *is* present in the source directory, so it starts successfully even with the override.

## Proposed Solution
Remove the volume mounts from `docker-compose.yml` for CI/production use, or ensure they don't override the build artifacts. Specifically for the `frontend` service in standalone mode, the volume mount is destructive.

## Next Steps
- Verify if removing volumes fixes the local startup (simulating CI).
- Check `nginx` logs if possible to see if it failed due to upstream resolution or dependency failure.
