#!/usr/bin/env node
/**
 * Debug Reddit submit page — dumps text field names/selectors
 * Run when logged in: npm run login:reddit first, then npm run debug:submit
 */

import readline from "readline";
import { launchBrowser, createStealthPage } from "../lib/browser.js";
import { openReddit } from "../lib/platforms/reddit.js";

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
const ask = (q) => new Promise((r) => rl.question(q, r));

(async () => {
  const browser = await launchBrowser({ headless: false, defaultViewport: null });
  const page = await createStealthPage(browser);

  await openReddit(page, true);
  await page.goto("https://www.reddit.com/r/test/submit/?type=TEXT", { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 3000));

  const info = await page.evaluate(() => {
    function collect(root) {
      let result = [];
      root.querySelectorAll("textarea, input, [contenteditable=true]").forEach((el) => {
        const rect = el.getBoundingClientRect();
        if (rect.width < 20 || rect.height < 20) return;
        result.push({
          tag: el.tagName,
          id: el.id || null,
          name: el.name || null,
          placeholder: (el.placeholder || el.getAttribute("data-placeholder") || "").slice(0, 50),
          type: el.type || null,
          contentEditable: el.contentEditable || null,
        });
      });
      root.querySelectorAll("*").forEach((el) => {
        if (el.shadowRoot) result = result.concat(collect(el.shadowRoot));
      });
      return result;
    }
    return { inputs: collect(document), url: window.location.href };
  });

  console.log("\n--- Reddit Submit Page (type=TEXT) ---");
  console.log("URL:", info.url);
  console.log("Text fields:", JSON.stringify(info.inputs, null, 2));

  await ask("\nPress Enter to close...");
  rl.close();
  await browser.close();
})();
