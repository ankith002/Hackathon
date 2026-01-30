#!/usr/bin/env node
/**
 * Login to Reddit — manual login, save cookies
 * 1. Opens Reddit login page
 * 2. You log in manually (solve CAPTCHA if needed)
 * 3. Press Enter when logged in
 * 4. Saves cookies for post script
 *
 * Usage: npm run login:reddit
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
  await page.goto("https://www.reddit.com/login", { waitUntil: "networkidle2" });

  console.log("\n📌 Log in manually in the browser.");
  console.log("   When you're on the Reddit home page, come back here.\n");

  await ask("Press Enter when you're logged in...");

  await saveCookies(page, "reddit");
  console.log("✅ Cookies saved. Run npm run post:reddit to post.");

  rl.close();
  await browser.close();
})();
