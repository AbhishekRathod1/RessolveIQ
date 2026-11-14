# Free Portfolio Demo Deployment

This setup publishes the frontend on Vercel and the FastAPI backend on Render. It makes a public URL for the demo; it does **not** make ResolveIQ production-ready.

## Important demo limitations

- The API has no authentication, authorization, or rate limiting. Anyone who finds the URL can create and change fictional tickets. Do not enter real names, email addresses, support tickets, credentials, or other private data.
- Render spins a free web service down after 15 minutes without inbound traffic; waking it takes about a minute.
- The free service uses an ephemeral filesystem. Ticket changes are lost on redeploy, restart, or idle spin-down. The start command reseeds the fictional sample tickets whenever the service starts.
- Keep the service on the free plan. Do not enable a paid instance or add billing-dependent resources unless you deliberately choose to do so.

## Deploy the backend to Render

1. Push the repository to GitHub and confirm the latest commit is on `main`.
2. Sign in to Render and choose **New +** -> **Blueprint**.
3. Connect `AbhishekRathod1/RessolveIQ` and select the `main` branch. Render will read the root `render.yaml`.
4. When prompted for `CORS_ORIGINS`, temporarily enter `["http://localhost:5173"]`. Keep the service on the Free plan and create it.
5. Wait for the build and deploy to finish. The build installs `backend/requirements.txt` and creates the local classifier artifact. The start command seeds fictional tickets and starts Uvicorn.
6. Copy the service's public URL, for example `https://resolveiq-abhis-demo-api.onrender.com`. Confirm that `<backend-url>/api/health` returns JSON.

If Render says the service name is unavailable, change `name` in `render.yaml` to a unique lowercase name, push the change, and retry the Blueprint sync.

## Deploy the frontend to Vercel

1. Sign in to Vercel and import the same GitHub repository.
2. Set **Root Directory** to `frontend`. Use the Vite preset, build command `npm run build`, and output directory `dist`.
3. Add the build environment variable `VITE_API_BASE_URL` with the value `<backend-url>/api`, using the actual Render URL from the previous section. Do not add a trailing slash.
4. Deploy and copy the Vercel production domain, for example `https://resolveiq-demo.vercel.app`.

The checked-in `frontend/vercel.json` routes React Router page URLs back to the Vite app.

## Allow the deployed frontend origin

1. In Render, open the backend service's **Environment** settings.
2. Change `CORS_ORIGINS` to a JSON array containing the exact Vercel production origin, for example `["https://resolveiq-demo.vercel.app"]`. Do not include a path or trailing slash.
3. Save and redeploy the backend.
4. Open the Vercel URL in a private/incognito window. Check that the dashboard loads, create a fictional ticket, and verify that the ticket appears in the list. If the Render service was asleep, allow about a minute for it to wake.

If you change the Vercel production domain, update `CORS_ORIGINS` and redeploy the backend.

## Resume link

After both services are deployed, use the Vercel production URL as the **Live demo** link and the GitHub URL as the **Source code** link:

- Live demo: `https://<your-vercel-production-domain>`
- Source code: <https://github.com/AbhishekRathod1/RessolveIQ>

The live URL does not exist until the Render and Vercel setup steps above have completed successfully.

## Provider documentation

- [Render Blueprint specification](https://render.com/docs/blueprint-spec)
- [Render free services](https://render.com/docs/free)
- [Vercel project configuration](https://vercel.com/docs/project-configuration/vercel-json)
