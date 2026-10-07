import { spawn, execSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { chromium } from "playwright";

const PORT = process.env.PORT ?? "3107";
const outDir = new URL("../screenshots/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
mkdirSync(outDir, { recursive: true });

const server = spawn("npx", ["next", "start", "-p", PORT], { stdio: "inherit", shell: true });
const base = `http://localhost:${PORT}`;

async function waitUp() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(base);
      if (r.ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("server did not start");
}

const viewports = [
  { name: "desktop-1440", width: 1440, height: 900 },
  { name: "mobile-390", width: 390, height: 844 },
  { name: "mobile-320", width: 320, height: 640 },
];

let failed = false;
try {
  await waitUp();
  const browser = await chromium.launch();
  for (const v of viewports) {
    const ctx = await browser.newContext({ viewport: { width: v.width, height: v.height }, reducedMotion: "reduce" });
    const page = await ctx.newPage();
    await page.goto(base, { waitUntil: "networkidle" });
    const qaResults = await page.evaluate(() => {
      const docWidth = document.documentElement.clientWidth;
      const docScrollWidth = document.documentElement.scrollWidth;
      const bodyScrollWidth = document.body.scrollWidth;
      const docOverflow = docScrollWidth > docWidth;
      const bodyOverflow = bodyScrollWidth > docWidth;

      const clippedElements = [];
      const visibleElements = Array.from(document.querySelectorAll("body *"));
      for (const el of visibleElements) {
        // Skip hidden or skip-link elements positioned offscreen intentionally
        if (el.classList.contains("skip-link") || el.classList.contains("sr-only")) continue;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) continue;
        if (rect.right > docWidth + 1 || rect.left < -1) {
          clippedElements.push({
            tag: el.tagName,
            className: el.className,
            right: Math.round(rect.right),
            left: Math.round(rect.left),
            docWidth,
            text: (el.textContent || "").trim().slice(0, 40),
          });
        }
      }

      return {
        docScrollWidth,
        docWidth,
        bodyScrollWidth,
        hasOverflow: docOverflow || bodyOverflow || clippedElements.length > 0,
        clippedElements,
      };
    });

    console.log(
      `${v.name}: docScrollWidth=${qaResults.docScrollWidth} clientWidth=${qaResults.docWidth} bodyScrollWidth=${qaResults.bodyScrollWidth} clippedCount=${qaResults.clippedElements.length} overflow=${qaResults.hasOverflow}`
    );
    if (qaResults.hasOverflow) {
      failed = true;
      console.error(`${v.name} clipped elements:`, JSON.stringify(qaResults.clippedElements, null, 2));
    }
    await page.screenshot({ path: `${outDir}${v.name}-full.png`, fullPage: true });
    await ctx.close();
  }
  await browser.close();
} finally {
  if (server.pid) {
    if (process.platform === "win32") {
      try {
        execSync(`taskkill /pid ${server.pid} /T /F`, { stdio: "ignore" });
      } catch {}
    } else {
      server.kill();
    }
  }
}
process.exit(failed ? 1 : 0);
