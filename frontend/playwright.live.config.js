import { defineConfig } from "@playwright/test";
// Real-input tests: real Sarvam + Gemini keys from backend/.env, response cache OFF, real speech fed as the microphone.
//   PW_FAKE_MIC=path/to/speech.wav npx playwright test -c playwright.live.config.js
const WEB = process.env.PW_WEB_PORT || "5176", API = process.env.PW_API_PORT || "8003";
const AUDIT = process.env.PW_AUDIT_DIR || "test-output";  // screenshots, PDFs and results stay inside the project (git-ignored)
const PYTHON = process.env.PW_PYTHON || "python";
const mic = process.env.PW_FAKE_MIC ? [`--use-file-for-fake-audio-capture=${process.env.PW_FAKE_MIC}`] : [];
export default defineConfig({
  testDir: "tests-live", timeout: 600000, workers: 1,
  outputDir: AUDIT + "/live-results",
  reporter: [["list"]],
  use: { baseURL: `http://127.0.0.1:${WEB}`, headless: true, screenshot: "only-on-failure", trace: "retain-on-failure", permissions: ["microphone"],
    launchOptions: { args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream", ...mic] } },
  webServer: [
    { command: `npm run dev -- --host 127.0.0.1 --port ${WEB} --strictPort`, url: `http://127.0.0.1:${WEB}`, reuseExistingServer: false, env: { VITE_API_BASE: `http://127.0.0.1:${API}` } },
    { command: `"${PYTHON}" -m uvicorn main:app --host 127.0.0.1 --port ${API}`, cwd: "../backend", url: `http://127.0.0.1:${API}`, reuseExistingServer: false,
      env: { VAANI_DATA_DIR: process.env.VAANI_DATA_DIR || "./data/live-test-data", VAANI_CACHE: "off", FRONTEND_URL: `http://127.0.0.1:${WEB}` } },
  ],
});
