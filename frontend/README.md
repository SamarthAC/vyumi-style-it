# VYUMI — Style it your way

A responsive React + TypeScript frontend for the supplied VYUMI FastAPI backend. Built with Vite, Tailwind CSS, original vector garment illustrations, and Lucide icons.

The application includes a searchable, filterable catalog; sorting; persistent saved pieces; a drag-and-drop portrait uploader; generation progress and polling; original/result comparison; downloads; retry and error states; mobile navigation; and accessible native dialogs. No account, checkout, or payment endpoints were present in the supplied backend, so those features are not fabricated.

## Development

Use Node.js 22.12+ or 24. From this directory:

```bash
npm ci
npm run dev
```

Vite runs on port 5173 and proxies `/api` to the FastAPI server on port 8000. In this cloud environment, start that server in another terminal:

```bash
cd /workspace/branch-snapshots/vyumi-style-it-feature-backend-catalog
/workspace/venvs/vyumi-backend/bin/python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```

To use another backend during development, set `API_PROXY_TARGET` before starting Vite. Alternatively, copy `.env.example` to `.env.local` and set `VITE_API_BASE_URL` to a browser-accessible HTTPS backend base URL. Environment values prefixed with VITE_ are public: never place credentials there. A direct cross-origin backend must permit the frontend origin through CORS.

## Demo and connected modes

Connected mode is the default. Catalog, health, original garment assets, uploads, generation, job polling, and results use the actual API contract. Real generation is enabled only when `/health` reports `engine_ready: true`. The supplied cloud backend currently has no configured GPU engine, so generation is unavailable; catalog and upload endpoints remain operational.

Toggle **Demo** above the collection to explore the entire UI without a backend or GPU. A demo portrait is optional, and personally selected photos stay in the browser tab. Demo results always use an explicitly labeled project reference image. They do not depict a transformation of your photo or the selected garment. Demo downloads contain the full original reference sheet.

Product illustrations are original SVG artwork, labeled in the UI. The current backend garment images are prototype placeholders. A link in the selected garment panel opens the actual backend asset.

## API integration

| Operation               | Endpoint                                                       |
| ----------------------- | -------------------------------------------------------------- |
| Catalog                 | GET /products                                                  |
| Backend / engine status | GET /health                                                    |
| Garment image           | GET /products/{product_id}/image                               |
| Upload portrait         | POST /style-it/upload, multipart field `file`                  |
| Start generation        | POST /style-it/generate, JSON `user_image_id` and `product_id` |
| Poll                    | GET /style-it/jobs/{job_id}                                    |
| Result                  | GET /style-it/results/{filename}                               |

Polling handles pending, processing, completed, and failed states, with an overall five-minute limit and per-request timeouts. Closing the dialog or cancelling stops frontend requests; it does not cancel a job already queued on the backend. Error details from HTTP responses and failed jobs are shown in the studio. Photos are checked locally for MIME type, size, decode integrity, and minimum dimensions; the backend supplies brightness and sharpness validation.

Saved garment IDs are stored in localStorage. Photos and generated results are not persisted by the frontend. Connected uploads are stored on the backend according to that service's retention policy. Do not upload sensitive images to this prototype.

## Build and deployment

```bash
npm run build
npm run preview
```

Deploy the generated `dist/` directory to your static host. Set `VITE_API_BASE_URL` **before building**, or configure your production reverse proxy to forward `/api/*` to the FastAPI backend with `/api` removed. Vite's development server configuration does not configure a production host. No production deployment has been performed.

## Browser tests

Start the backend, then:

```bash
npx playwright install chromium
npm test
```

On machines with an existing Chromium binary, use `CHROMIUM_EXECUTABLE=/path/to/chromium npm test`. The Playwright configuration starts Vite if needed.

Tests exercise real backend catalog and upload endpoints, favorites, filtering, sorting, input validation, demo results and downloads, offline fallbacks, mobile layout, and generation integration. Generation success and failure responses are intercepted by the tests because real GPU inference is unavailable. They do not validate CatVTON image generation.

## Source and license notes

The frontend was built in the originally empty `Dhanush-singh-g/VYUMI-TEMP-STYLE` checkout. The three uploaded backend branch snapshots remain separate and unchanged. The private original GitHub repository is not currently accessible through this environment's Git credentials.

`public/tryon-example.png` is copied without modification from `feature/tryon-engine/docs/sample/154939.png`, supplied by the user. It appears in the editorial hero and explicitly labeled demo. The upstream project documents CatVTON model usage as **CC BY-NC-SA 4.0**, for internal non-commercial research/prototype use. Review the reference asset's rights and replace it with suitable licensed material before any commercial publication.
