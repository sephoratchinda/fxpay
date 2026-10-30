# Cloud Deployment (Render)

1. Push this repository to GitHub.
2. Render dashboard -> **New -> Blueprint** -> select the repo. `render.yaml` provisions a PostgreSQL database, the Django API (Docker) and the React site (Docker/nginx).
3. After the first deploy copy the API URL (e.g. `https://fxpay-api.onrender.com`). Edit `VITE_API_URL` of `fxpay-web` to `https://fxpay-api.onrender.com/api` and redeploy the site (it is baked in at build time).
4. Verify `https://<api>/api/health/` returns `{"status":"ok"}`, then open the web URL and register.
5. Take screenshots of the Render dashboard (services "Live"), health endpoint and the running app - these are your deployment evidence.

Notes: on the free plan the API sleeps after inactivity (first request ~30 s). Set `ALLOWED_HOSTS` / `CORS_ORIGINS` env vars to your domains for tighter security (and `CORS_ALLOW_ALL=0`).

### AWS / Azure alternative
Build both Docker images, push to ECR/ACR, run as ECS Fargate / Azure Container Apps with managed PostgreSQL (RDS / Azure Database for PostgreSQL) and set `DATABASE_URL`, `SECRET_KEY`, `DEBUG=0`.

### Git workflow suggestion
`main` (stable) <- `develop` <- feature branches: `feat/payments`, `feat/fx-risk`, `feat/optimizer`, `feat/dashboard`, `feat/ai`, `docs`. Commit per module with messages like `feat(fx): add forward contract simulation`.
