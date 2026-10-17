// Real end-to-end test. No demo buttons, no cache: real speech -> Sarvam STT -> agent -> extraction -> approval -> BRD + app.
// Then the same browser tab switches to a different real request, and nothing from the first may leak into the second.
import { test, expect } from "@playwright/test";

const CLINIC_WORDS = /dental|clinic|appointment|patient|डेंटल|क्लिनिक|अपॉइंटमेंट|मरीज़|मरीज/i;
// What Sarvam Saaras v4 (codemix) transcribed from clinic_owner.wav in the baseline run.
const SPOKEN_CLINIC = "[Owner] मैं Pune में एक छोटा dental clinic चलाती हूँ। अभी सारी appointment एक register में लिखते हैं और मरीज़ों को याद दिलाना भूल जाते हैं। मुझे एक आसान app चाहिए जिसमें मरीज़ WhatsApp से appointment book कर सकें। सुबह 10 बजे से शाम 7 बजे तक। appointment से एक दिन पहले मरीज़ को reminder message जाना चाहिए।";
const ROOMMATES = [
  "[Owner] हम चार रूममेट हैं और किराया, बिजली और राशन का खर्च आपस में बांटते हैं। हर महीने हिसाब में झगड़ा होता है।",
  "[Owner] मुझे एक ऐप चाहिए जिसमें कोई भी खर्च डाले तो वो अपने आप चार लोगों में बंट जाए।",
  "[Owner] अगर कोई पाँच सौ रुपये से ज़्यादा का सामान खरीदे तो बाकी सबको नोटिफिकेशन जाना चाहिए।",
].join("\n");

test("real voice, real answers, then a different real request in the same tab", async ({ page }) => {
  const times = {}, notes = [];
  const lap = async (name, fn) => { const t = Date.now(); await fn(); times[name] = ((Date.now() - t) / 1000).toFixed(1) + " s"; };
  page.on("console", m => { if (m.type() === "error") notes.push("console error: " + m.text().slice(0, 160)); });
  const approveAll = async reviewer => {
    const fast = page.getByRole("region", { name: "Fast approval" });
    if (await fast.count() && await fast.getByRole("button", { name: /Approve \d+ verified/ }).isEnabled()) {
      await fast.getByLabel("Reviewer name").fill(reviewer);
      await fast.getByRole("button", { name: /Approve \d+ verified/ }).click();
    } else {
      if (await fast.count()) await fast.getByLabel("Reviewer name").fill(reviewer);
      await page.getByRole("button", { name: "Review and approve" }).click();
      await page.getByLabel("Reviewer name").fill(reviewer);
    }
    let clicks = 0;
    while (await page.getByRole("heading", { name: "Source-backed sign-off" }).count()) { await page.getByRole("button", { name: /^Approve/ }).first().click(); clicks++; }
    return clicks;
  };

  await page.goto("/");
  await page.getByRole("button", { name: "हिंदी", exact: true }).click();
  await page.getByRole("button", { name: "Start capturing" }).click();

  if (process.env.PW_INPUT === "typed") {
    // Typed real input: the exact transcript Sarvam produced from the real speech in the 17 Oct baseline run.
    await page.getByLabel("Transcript", { exact: true }).fill(SPOKEN_CLINIC);
    times["1. input"] = "typed (Sarvam key unavailable)";
  } else {
    // 1. Speak: the fake microphone plays real Hindi speech (26 s).
    await page.getByRole("button", { name: "Record microphone" }).click();
    await page.waitForTimeout(27000);
    await lap("1. speech -> transcript after Stop", async () => {
      await page.getByRole("button", { name: "Stop recording" }).click();
      await expect(page.getByLabel("Transcript", { exact: true })).toHaveValue(/क्लिनिक|अपॉइंटमेंट|रजिस्टर|व्हाट्सऐप|clinic|appointment/i, { timeout: 90000 });
      await expect(page.getByRole("button", { name: /Next: agent checks for gaps/ })).toBeEnabled({ timeout: 90000 });
    });
  }
  notes.push("transcript: " + (await page.getByLabel("Transcript", { exact: true }).inputValue()).replace(/\n/g, " / ").slice(0, 300));

  // 2. Agent questions, answered by typing like a real owner.
  await lap("2. agent's first question", async () => {
    await page.getByRole("button", { name: /Next: agent checks for gaps/ }).click();
    await expect(page.locator(".question-card")).toBeVisible({ timeout: 90000 });
  });
  notes.push("completeness after speech: " + await page.locator(".meter-pct").innerText() + " | " + (await page.locator(".meter-card .source-note").first().innerText()).slice(0, 120)
    + ((await page.locator(".meter-card .notice").count()) ? " | WARNING: " + await page.locator(".meter-card .notice").innerText() : ""));
  const answers = ["रिसेप्शनिस्ट और मैं, दो लोग इसे इस्तेमाल करेंगे, और लगभग सौ मरीज़।", "हमें यह अगले महीने तक चाहिए।", "बजट लगभग पचास हज़ार रुपये है।"];
  for (let i = 0; i < answers.length && await page.locator(".question-card").count(); i++) {
    notes.push(`Q${i + 1}: ` + (await page.locator(".question-card").innerText()).split("\n").slice(0, 3).join(" | ").slice(0, 200));
    await page.getByLabel(/Answer in/).fill(answers[i]);
    const before = await page.locator(".question-card").innerText();
    await lap(`3.${i + 1} next question after answer ${i + 1}`, async () => {
      await page.getByRole("button", { name: "Save answer →" }).click();
      // Wait for the NEXT question to be on screen (or the "all done" card), not merely for the old card to disappear.
      await expect.poll(async () => {
        if (await page.locator(".done-card").count()) return "done";
        if (!(await page.locator(".question-card").count())) return "waiting";
        const now = await page.locator(".question-card").innerText();
        return now === before ? "waiting" : "next";
      }, { timeout: 90000, intervals: [100] }).not.toBe("waiting");
    });
  }

  // 3. Extraction and review.
  await lap("4. extraction (+ conflicts)", async () => {
    await page.getByRole("button", { name: "Extract requirements →" }).click();
    await expect(page.locator(".rule-editor").first()).toBeVisible({ timeout: 90000 });
  });
  notes.push("rules: " + (await page.locator(".rule-editor legend").allInnerTexts()).join(" | "));

  // 4. Approval, the way the UI offers it.
  const tApprove = Date.now();
  const clicks = await approveAll("Dr. Mehta");
  times["5. approval"] = `${clicks} screens clicked, ${((Date.now() - tApprove) / 1000).toFixed(1)} s`;
  await lap("6. BRD sections + AI app ready", async () => {
    await expect(page.locator(".ai-bar")).toContainText(/AI drafted/, { timeout: 120000 });
    await expect(page.locator(".brd-app-col iframe")).toHaveAttribute("srcdoc", /<html/i, { timeout: 120000 });
    await expect(page.locator(".brd-app-col")).not.toContainText("still being built", { timeout: 120000 });
  });
  const brd1 = await page.locator(".brd-doc").innerText();
  notes.push("session 1 BRD mentions the clinic: " + CLINIC_WORDS.test(brd1));

  // 5. Same tab: go back and give a completely different real request (what happened in the failed test).
  while (!(await page.getByLabel("Transcript", { exact: true }).count())) await page.getByRole("button", { name: /Back/ }).click();
  await page.getByLabel("Transcript", { exact: true }).fill(ROOMMATES);
  await page.getByRole("button", { name: /Next: agent checks for gaps/ }).click();
  await expect(page.locator(".meter-pct")).toBeVisible({ timeout: 90000 });
  await page.getByRole("button", { name: "Extract requirements →" }).click();
  await expect(page.locator(".rule-editor").first()).toBeVisible({ timeout: 90000 });
  await approveAll("Rahul");
  await lap("7. second session BRD + app ready", async () => {
    await expect(page.locator(".ai-bar")).toContainText(/AI drafted/, { timeout: 120000 });
    await expect(page.locator(".brd-app-col")).not.toContainText("still being built", { timeout: 120000 });
  });
  await page.waitForTimeout(15000);  // give any late background result from session 1 time to arrive, as it did in the failed test
  const brd2 = await page.locator(".brd-doc").innerText();
  const app2 = await page.locator(".brd-app-col iframe").getAttribute("srcdoc");
  notes.push("session 2 title: " + await page.locator(".brd-final h1").first().innerText());
  console.log("REAL TEST\n" + JSON.stringify(times, null, 1) + "\n" + notes.join("\n"));
  expect(CLINIC_WORDS.test(brd2), "session 2 BRD must not contain session 1 (clinic) content").toBe(false);
  expect(CLINIC_WORDS.test(app2 || ""), "session 2 app must not contain session 1 (clinic) content").toBe(false);
  expect(brd2).toMatch(/रूममेट|roommate|खर्च|expense|split|बंट/i);
});
