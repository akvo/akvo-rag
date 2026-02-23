---
trigger: always_on
---

## Docker Commands

**All commands MUST be executed via `./dev.sh`. Never run bare commands outside Docker.**

### Service Access URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:80 (or http://localhost:81, http://127.0.0.1.nip.io) |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| Flower | http://localhost:5555 |
| RabbitMQ Management | http://localhost:15672 |

### Environment Management

```bash
./dev.sh up -d           # Start all services
./dev.sh down            # Stop all services
./dev.sh ps              # View running services
./dev.sh logs -f         # Follow all logs
./dev.sh logs backend    # View specific service logs
```

### Backend Commands

```bash
./dev.sh exec backend ./test.sh                          # Run all backend tests
./dev.sh exec backend ./test-unit.sh                     # Run unit tests only
./dev.sh exec backend bash                               # Open shell
./dev.sh exec backend python -m app.seeder.seed_prompts  # Seed prompts
```

### Frontend Commands

```bash
./dev.sh exec frontend pnpm lint                        # Run ESLint
./dev.sh exec frontend pnpm build                       # Build frontend
./dev.sh exec frontend bash                             # Open shell
```

### Rules

1. **Never run `python`, `pip`, `node`, `pnpm`, or `npm` directly** — always prefix with `./dev.sh exec backend` or `./dev.sh exec frontend`
2. **Database migrations** run automatically on backend startup via Alembic
3. **Hot reload** is enabled for all development services
4. **Environment variables** go in `.env` file (based on `.env.example`)
5. **Testing** must ALWAYS be executed inside the Docker container.
