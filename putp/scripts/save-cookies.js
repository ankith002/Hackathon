#!/usr/bin/env node
/**
 * Save Reddit cookies after manual login
 * 1. Run this script
 * 2. Log in manually in the browser that opens
 * 3. Press Enter in terminal when done
 * Cookies will be saved to cookies/reddit.json
 */

import readline from "readline";
import { launchBrowser, createStealthPage } from "../lib/browser.js";
import { saveCookies } from "../lib/cookies.js";

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
const ask = (q) => new Promise((r) => rl.question(q, r));

(async () => {
  const browser = await launchBrowser({
    headless: false,
    defaultViewport: null,
  });

  const page = await createStealthPage(browser);
  await page.goto("https://www.reddit.com", { waitUntil: "networkidle2" });

  console.log("\n📌 Log in manually in the browser window.");
  console.log("   When you're logged in and see the Reddit feed, come back here.\n");

  await ask("Press Enter when you're logged in to save cookies...");

  await saveCookies(page, "reddit");
  console.log("✅ Cookies saved to cookies/reddit.json");

  rl.close();
  await browser.close();
})();
