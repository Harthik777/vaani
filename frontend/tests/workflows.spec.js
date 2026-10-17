import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import path from "node:path";
const AUDIT = process.env.PW_AUDIT_DIR || "../../../audit";

// The test backend runs with USE_REAL_LLM=false and USE_REAL_SARVAM=false: every AI/Sarvam path must degrade honestly.
const MODES = { business: "Business requirements (BRD)", awareness: "Public awareness", audit: "Field audit", deals: "B2B deals" };
async function start(page, mode = "business", lang = "English") {
  await page.goto("/?modes=all");  // the landing page shows only the BRD flow unless ?modes=all
  await page.getByRole("button", { name: new RegExp(MODES[mode].replace(/[()]/g, "\\$&")) }).click();
  await page.getByRole("button", { name: lang, exact: true }).click();
  await page.getByRole("button", { name: "Start capturing" }).click();
}
async function toReview(page) {
  await page.getByRole("button", { name: /Next: agent checks for gaps/ }).click();
  await expect(page.getByRole("heading", { name: "The agent's questions" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Extract requirements →" })).toBeEnabled();
  await page.getByRole("button", { name: "Extract requirements →" }).click();
  await expect(page.getByRole("button", { name: "Review and approve" })).toBeEnabled();
  await vendorView(page);
}
// The Review step opens in the owner's read-only view; edits in these tests need the vendor view.
async function vendorView(page) {
  const toggle = page.getByRole("button", { name: /Vendor view/ });
  if (await toggle.count()) await toggle.click();
}
async function draft(page, mode = "business") {
  await start(page, mode);
  await page.getByRole("button", { name: "Use demo", exact: true }).click();
  await toReview(page);
}
const signoff = page => page.getByRole("button", { name: "Review and approve" }).click();
async function approveRemaining(page) {
  const approve = page.getByRole("button", { name: /^Approve/ });
  while (await approve.count()) await approve.first().click();
  await expect(page.getByRole("button", { name: "PDF", exact: true })).toBeVisible();
}

for (const [mode] of Object.entries(MODES)) test(mode + ": edit, skip, reload, publish and use responsive portal", async ({ page, context }) => {
  const errors = []; page.on("pageerror", e => errors.push(e.message));
  await draft(page, mode);
  const first = page.locator(".rule-editor").first();
  const rejectedTitle = await first.getByLabel("Title", { exact: true }).inputValue();
  await page.locator(".rule-editor").nth(1).getByLabel("Then / action", { exact: true }).fill("Reviewed unique action " + mode);
  await page.reload();
  await expect(page.locator(".rule-editor").nth(1).getByLabel("Then / action", { exact: true })).toHaveValue("Reviewed unique action " + mode);
  await signoff(page);
  await page.getByRole("button", { name: "Skip requirement", exact: true }).click();
  await approveRemaining(page);
  await expect(page.locator(".brd-doc")).not.toContainText(rejectedTitle);
  await expect(page.locator(".brd-doc")).toContainText("Reviewed unique action " + mode);
  await expect(page.locator(".brd-doc")).toContainText("FR-01");
  await expect(page.locator(".brd-doc")).not.toContainText("FastAPI");
  // No AI configured: the BRD says so instead of pretending, and the app is labelled as a template.
  await expect(page.locator(".ai-bar")).toContainText("not configured");
  await expect(page.locator(".brd-app-col")).toContainText(mode === "business" ? "Requirement simulator" : "Template");
  expect(await page.locator(".brd-app-col iframe").getAttribute("srcdoc")).toContain("Content-Security-Policy");
  await page.getByRole("button", { name: "Publish reviewed version", exact: true }).click();
  await expect(page.getByLabel("Shareable URL")).toBeVisible();
  const url = await page.getByRole("link", { name: "Open responsive portal" }).getAttribute("href");
  const published = await context.newPage(); await published.goto(url);
  await expect(published.locator(".portal-layout")).toBeVisible();
  await expect(published.locator(".portal-document")).toContainText("Reviewed unique action " + mode);
  await expect(published.locator(".portal-document")).not.toContainText(rejectedTitle);
  if (mode !== "awareness") {
    const unauthenticated = await context.newPage(); await unauthenticated.goto(url.split("#")[0]);
    await expect(unauthenticated.getByRole("heading", { name: "Portal unavailable" })).toBeVisible(); await unauthenticated.close();
  } else {
    await expect(published.getByRole("link", { name: "Call 104", exact: true })).toHaveAttribute("href", "tel:104");
    await expect(published.getByRole("link", { name: /Find primary health centers/ })).toHaveAttribute("href", /maps\/search/);
  }
  await published.setViewportSize({ width: 390, height: 844 });
  expect(await published.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await published.screenshot({ path: AUDIT + "/portal-" + mode + "-mobile.png", fullPage: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: AUDIT + "/final-" + mode + "-desktop.png", fullPage: true });
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".brd-app-col")).toBeHidden();
  await expect(page.locator(".brd-doc")).toBeVisible();
  await page.pdf({ path: AUDIT + "/sample-" + mode + ".pdf", format: "A4", printBackground: true });
  expect(errors).toEqual([]); await published.close();
});

test("Meeting demo: agent interview, conflict, verifier, full BRD and exports", async ({ page }) => {
  const errors = []; page.on("pageerror", e => errors.push(e.message));
  await start(page, "business", "English");
  await page.getByRole("button", { name: "Use 2-speaker meeting demo" }).click();
  await expect(page.getByLabel("Transcript", { exact: true })).toHaveValue(/\[Manager\]/);
  await page.getByRole("button", { name: /Next: agent checks for gaps/ }).click();
  await expect(page.locator(".meter-pct")).toHaveText("38%");
  await expect(page.locator(".ck-covered")).toHaveCount(3);
  await expect(page.locator(".question-card")).toContainText("Users and stakeholders");
  await page.getByRole("button", { name: "Use sample answer" }).click();
  await page.getByRole("button", { name: "Save answer →" }).click();
  await expect(page.locator(".meter-pct")).toHaveText("50%");
  await expect(page.locator(".question-card")).toContainText("Timeline");
  await page.getByRole("button", { name: "Use sample answer" }).click();
  await page.getByRole("button", { name: "Save answer →" }).click();
  await expect(page.locator(".meter-pct")).toHaveText("63%");
  await page.getByRole("button", { name: /^Skip/ }).click();
  await expect(page.locator(".ck-skipped")).toHaveCount(1);
  await page.screenshot({ path: AUDIT + "/meeting-1-interview.png", fullPage: true });
  await page.getByRole("button", { name: "Extract requirements →" }).click();

  // Owner said 50 kg, Manager said 100 kg: the agent surfaces it with both speakers.
  const conflict = page.locator(".conflict-card");
  await expect(conflict).toContainText("Stakeholders disagree");
  await expect(conflict).toContainText("Owner");
  await expect(conflict).toContainText("Manager");
  await expect(page.locator(".verifier")).toContainText("5 verified");
  await page.screenshot({ path: AUDIT + "/meeting-2-review.png", fullPage: true });
  await conflict.getByRole("button", { name: "Keep Manager's version" }).click();
  await expect(page.locator(".conflict-card")).toHaveCount(0);
  await expect(page.locator(".owner-card")).toHaveCount(4);
  await vendorView(page);
  await expect(page.locator(".rule-editor")).toHaveCount(4);

  // A user edit that introduces an unspoken number is caught immediately.
  await page.locator(".rule-editor").first().getByLabel("Then / action", { exact: true }).fill("require the owner's approval within 48 hours");
  await expect(page.locator(".rule-editor").first()).toContainText("48 (not spoken)");
  await page.locator(".rule-editor").first().getByLabel("Then / action", { exact: true }).fill("require the owner's approval before dispatch");

  await signoff(page);
  await expect(page.getByLabel("Reviewer name")).toHaveValue("Demo reviewer");
  await approveRemaining(page);
  const doc = page.locator(".brd-doc");
  await expect(doc).toContainText("Stakeholders and users");
  await expect(doc).toContainText("12 people");
  await expect(doc).toContainText("Diwali");
  await expect(doc).toContainText("Open questions");
  await expect(doc).toContainText("Budget: What budget");
  await expect(doc).toContainText("FR-04");
  await expect(doc.locator(".speaker-chip").first()).toBeVisible();
  await expect(page.locator(".sarvam-strip")).toContainText("Powered by Sarvam");
  await expect(page.getByRole("region", { name: "Download BRD" })).toBeVisible();
  await expect(page.locator(".brd-app-col")).toContainText("· English");

  const md = page.waitForEvent("download");
  await page.getByRole("button", { name: "Markdown" }).click();
  const markdown = await readFile(await (await md).path(), "utf-8");
  expect(markdown).toContain("| FR-01 |");
  expect(markdown).toContain("Open questions");
  const csv = page.waitForEvent("download");
  await page.getByRole("button", { name: "Jira CSV" }).click();
  const jira = await readFile(await (await csv).path(), "utf-8");
  expect(jira).toContain('"Summary","Issue Type"');
  expect(jira).toContain("FR-01");
  const word = page.waitForEvent("download");
  await page.getByRole("button", { name: "Word (.docx)" }).click();
  const docx = await readFile(await (await word).path());
  expect(docx.subarray(0, 2).toString()).toBe("PK");
  await expect(page.locator(".brd-app-col")).toContainText("Requirement simulator");
  const app = page.frameLocator(".brd-app-col iframe");
  await expect(app.locator("body")).toContainText("FR-01");
  await expect(app.locator("body")).toContainText("No action (< 100 kg)");
  await app.getByRole("slider", { name: /Low-stock reorder alert/ }).evaluate(el => { el.value = "40"; el.dispatchEvent(new Event("input", { bubbles: true })); });
  await expect(app.locator("body")).toContainText("Rule applies → send the reorder alert");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: AUDIT + "/final-meeting-desktop.png", fullPage: true });
  expect(errors).toEqual([]);
});

test("Hindi meeting demo keeps Hindi quotes and finds the conflict", async ({ page }) => {
  await start(page, "business", "हिंदी");
  await page.getByRole("button", { name: "Use 2-speaker meeting demo" }).click();
  await toReview(page);
  await expect(page.locator(".conflict-card")).toContainText("50 kg");
  await expect(page.locator(".rule-editor").first().getByLabel("Exact source text")).toHaveValue(/इलायची/);
});

test("Deaf/HoH typed flow, back navigation, all skipped, and mode reset", async ({ page }) => {
  await page.goto("/"); await page.getByText("More options", { exact: false }).click(); await page.getByRole("button", { name: /Deaf \/ HoH/ }).click();
  await page.getByRole("button", { name: "Start capturing" }).click();
  await expect(page.getByRole("button", { name: "Record microphone" })).toHaveCount(0);
  await page.getByLabel("Transcript", { exact: true }).fill("When stock is low, place a new order.");
  await page.getByRole("button", { name: "Enter rules manually" }).click();
  await page.getByRole("button", { name: "Add requirement" }).click();
  await page.getByLabel("Title", { exact: true }).fill("Manual stock rule");
  await page.getByLabel("If / context").fill("stock is low"); await page.getByLabel("Then / action").fill("place a new order");
  await page.getByLabel("Exact source text").fill("When stock is low, place a new order.");
  await expect(page.locator(".rule-editor")).toContainText("Verified against speech");
  await signoff(page); await page.getByLabel("Reviewer name").fill("Test reviewer");
  await page.getByRole("button", { name: "Skip requirement" }).click();
  await expect(page.locator(".brd-doc")).not.toContainText("Manual stock rule");
  await page.getByRole("button", { name: "Publish reviewed version", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Approve at least one");
  await page.getByRole("button", { name: "Back", exact: false }).click();
  await expect(page.getByRole("heading", { name: "Source-backed sign-off" })).toBeVisible();
});

test("Live text cannot silently become demo rules and edits invalidate approval", async ({ page }) => {
  await draft(page); await signoff(page); await approveRemaining(page);
  for (let i = 0; i < 4; i++) await page.getByRole("button", { name: "Back", exact: false }).click();
  if (!(await page.locator(".tx-edit").evaluate(e => e.open))) await page.getByText("Edit the words", { exact: true }).click();
  await page.getByLabel("Transcript", { exact: true }).fill("These are real custom words.");
  await toReviewExpectingFailure(page);
  await expect(page.locator(".rule-editor")).toHaveCount(0);
  expect(await page.evaluate(() => JSON.parse(sessionStorage.getItem("vaani_session")).approved)).toEqual([]);
});
async function toReviewExpectingFailure(page) {
  await page.getByRole("button", { name: /Next: agent checks for gaps/ }).click();
  await expect(page.locator(".meter-pct")).toHaveText("0%");
  await page.getByRole("button", { name: "Extract requirements →" }).click();
  await expect(page.getByRole("alert")).toContainText("not configured");
}

test("Milestone clearance requires a passed quality inspection (published deal portal)", async ({ page, context }) => {
  await draft(page, "deals"); await signoff(page); await approveRemaining(page);
  await page.getByRole("button", { name: "Publish reviewed version", exact: true }).click();
  const url = await page.getByRole("link", { name: "Open responsive portal" }).getAttribute("href");
  const portal = await context.newPage(); await portal.goto(url);
  await portal.getByLabel("Advance paid", { exact: true }).check(); await portal.getByLabel("Dispatched", { exact: true }).check();
  await expect(portal.getByLabel("Balance settled", { exact: true })).toBeDisabled();
  await portal.getByRole("button", { name: "Prepare milestone payment" }).click();
  await expect(portal.getByText("Payment integration is deferred. No payment is initiated.", { exact: true })).toBeVisible();
  await portal.getByLabel("Inspector", { exact: true }).fill("Warehouse reviewer");
  await portal.getByLabel("Measured shrinkage (%)").fill("3");
  await portal.getByRole("combobox", { name: "Outcome", exact: true }).selectOption("pass");
  await portal.getByRole("button", { name: "Save inspection" }).click();
  await portal.getByLabel("Quality inspection passed", { exact: true }).check();
  await expect(portal.getByLabel("Balance settled", { exact: true })).toBeEnabled();
});

test("Meeting and notes uploads degrade honestly without Sarvam", async ({ page }) => {
  await page.goto("/"); await page.getByRole("button", { name: "Start capturing" }).click();
  await page.locator('.import-btn input[type=file]').first().setInputFiles({ name: "call.wav", mimeType: "audio/wav", buffer: Buffer.from("RIFFfake") });
  await expect(page.getByRole("alert")).toContainText("needs Sarvam");
  await page.locator('.import-btn input[type=file]').nth(1).setInputFiles({ name: "notes.png", mimeType: "image/png", buffer: Buffer.from("PNGfake") });
  await expect(page.getByRole("alert")).toContainText("Doc AI");
  await expect(page.getByLabel("Transcript", { exact: true })).toHaveValue("");
});

test("Standalone build works offline with the demo", async ({ page }) => {
  const filePath = path.resolve("../vaani-prototype.html");
  const content = await readFile(filePath, "utf-8");
  expect(content.length).toBeGreaterThan(100000);
  await page.context().setOffline(true);
  await page.goto(pathToFileURL(filePath).href);
  await page.getByRole("button", { name: "Start capturing" }).click(); await page.getByRole("button", { name: "Use demo", exact: true }).click();
  await toReview(page); await signoff(page); await approveRemaining(page);
  await expect(page.locator(".brd-doc")).toContainText("Business Requirements Document");
});

test("Real MediaRecorder retains original audio and reload restores playback", async ({ browser }) => {
  const context = await browser.newContext({ permissions: ["microphone"] });
  const page = await context.newPage();
  await page.goto("/"); await page.getByRole("button", { name: "Start capturing" }).click();
  await page.getByRole("button", { name: "Record microphone" }).click();
  await expect(page.getByRole("button", { name: "Stop recording" })).toBeVisible();
  await page.waitForTimeout(600); await page.getByRole("button", { name: "Stop recording" }).click();
  await expect(page.locator("audio")).toBeVisible();
  await expect(page.getByRole("alert")).toContainText("not configured");
  await page.reload(); await expect(page.locator("audio")).toBeVisible();
  const evidence = await page.evaluate(() => JSON.parse(sessionStorage.getItem("vaani_session")).evidence);
  expect(evidence).toHaveLength(1); expect(evidence[0].sha256).toMatch(/^[a-f0-9]{64}$/); expect(evidence[0].speaker).toBe("Owner");
  expect(await page.getByLabel("Transcript", { exact: true }).inputValue()).toBe("");
  await context.close();
});
