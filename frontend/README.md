# ResolveIQ frontend

React, TypeScript, Vite, Tailwind CSS, Recharts, React Router, and Lucide-powered support workspace.

## Run locally

Start the FastAPI backend first. Then, from this directory:

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

The app runs at <http://localhost:5173>. Set `VITE_API_BASE_URL` in `.env.local` if the backend is not at `http://127.0.0.1:8000/api`.

Run `npm run lint` and `npm run build` to validate the frontend.
