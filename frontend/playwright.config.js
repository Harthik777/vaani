import { defineConfig } from "@playwright/test";
// Ports are configurable so the suite can run while the normal dev servers (5173/8000) are open:
//   PW_WEB_PORT=5174 PW_API_PORT=8001 npx playwright test
const WEB = process.env.PW_WEB_PORT || "5173", API = process.env.PW_API_PORT || "8000";
// Portable paths: PW_AUDIT_DIR (screenshots, PDFs, results), PW_PYTHON (interpreter with backend deps), VAANI_DATA_DIR.
const AUDIT = process.env.PW_AUDIT_DIR || "test-output";  // screenshots, PDFs and results stay inside the project (git-ignored)
const PYTHON = process.env.PW_PYTHON || "python";
const DATA = process.env.VAANI_DATA_DIR || "./data/test-data";
export default defineConfig({
  testDir: "tests", timeout: 45000, workers: 1,
  outputDir: AUDIT + "/browser-results",
  reporter: [["list"], ["json", { outputFile: AUDIT + "/browser-results.json" }]],
  use: { baseURL: `http://127.0.0.1:${WEB}`, headless: true, screenshot: "only-on-failure", trace: "retain-on-failure", acceptDownloads: true, launchOptions: { args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"] } },
  webServer: [
    { command: `npm run dev -- --host 127.0.0.1 --port ${WEB} --strictPort`, url: `http://127.0.0.1:${WEB}`, reuseExistingServer: false, env: { VITE_API_BASE: `http://127.0.0.1:${API}` } },
    { command: `"${PYTHON}" -m uvicorn main:app --host 127.0.0.1 --port ${API}`, cwd: "../backend", url: `http://127.0.0.1:${API}`, reuseExistingServer: false,
      env: { VAANI_DATA_DIR: DATA, VAANI_CACHE: "off", FRONTEND_URL: `http://127.0.0.1:${WEB}`, USE_REAL_LLM: "false", USE_REAL_SARVAM: "false" } },
  ],
});
