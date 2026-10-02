# BrandShield AI

BrandShield AI is a React + Vite script safety-review interface with a FastAPI and LangGraph backend. The graph runs independent checks for tone/toxicity, originality/IP risk, and cultural sensitivity, then combines their scores into one report.

## Stack

- Frontend: React, Vite, and Lucide
- Backend: FastAPI and LangGraph
- LLM provider: Groq (optional; configure `GROQ_API_KEY` for LLM-based analysis)
- Hosting: Netlify (frontend) and Render (backend)

## Run locally

Install frontend dependencies once:

```powershell
npm install
```

Start the backend in the first PowerShell terminal:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001
```

Start the frontend in a second terminal:

```powershell
$env:VITE_API_PROXY_TARGET = "http://127.0.0.1:8001"
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open <http://localhost:5173/>. The Vite development server proxies `/api` requests to the backend.

## Deploy the backend to Render

1. Push this project to a GitHub repository and create a Render Blueprint from that repository.
2. Render reads `render.yaml`; the API build installs the lightweight production dependencies from `backend/requirements.txt`.
3. Set the requested `GROQ_API_KEY` secret in Render. `GROQ_MODEL` and the Python version are defined in the blueprint.
4. Deploy and wait for the service health check at `/health` to pass.
5. Copy the service URL, for example `https://brandshield-ai-api.onrender.com`.

The Render service starts with:

```text
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

## Deploy the frontend to Netlify

1. Import the same GitHub repository in Netlify.
2. Netlify reads `netlify.toml`; the build command is `npm run build` and the publish directory is `dist`.
3. Add the Netlify environment variable `VITE_API_URL`, with the full Render endpoint, for example:
   `https://brandshield-ai-api.onrender.com/api/analyze`
4. Trigger a fresh Netlify deploy after setting the variable; Vite embeds it during the build.
5. Copy the deployed production site URL, for example `https://your-site.netlify.app`.

`netlify.toml` also provides the SPA fallback so direct page loads work.

## Connect Netlify to Render

After Netlify has assigned the site URL, set `CORS_ORIGINS` in the Render service environment to the exact Netlify production origin, without a trailing slash. For example:

```text
https://your-site.netlify.app
```

For a custom domain, include both origins comma-separated:

```text
https://your-site.netlify.app,https://brandshield.example
```

Save the Render environment change and let the service restart. Set this to trusted frontend origins only. The API can be checked at `https://your-render-service.onrender.com/health`.

## Environment variables

| Variable | Where | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | Render | Enables Groq-backed analysis; never expose it in frontend variables |
| `GROQ_MODEL` | Render | Groq model identifier; defaults in `render.yaml` |
| `CORS_ORIGINS` | Render | Comma-separated exact frontend origins allowed to call the API |
| `VITE_API_URL` | Netlify | Full `/api/analyze` endpoint on Render, set before frontend build |
| `VITE_API_PROXY_TARGET` | Local frontend terminal | Backend origin used by the Vite development proxy |

## Build locally

```powershell
npm run build
```

The browser UI has a local heuristic preview fallback if the API cannot be reached. For production AI-based analysis, configure `GROQ_API_KEY` on Render and set the Netlify API URL and Render CORS origin as described above.
