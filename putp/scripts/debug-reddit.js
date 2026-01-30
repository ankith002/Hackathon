#!/usr/bin/env node
/**
 * Debug Reddit page structure - run this to see what selectors exist
 * Helps fix login/post when Reddit changes their UI
 */

import "dotenv/config";
import readline from "readline";
import { launchBrowser, createStealthPage } from "../lib/browser.js";

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
const ask = (q) => new Promise((r) => rl.question(q, r));

(async () => {
  const browser = await launchBrowser({ headless: false, defaultViewport: null });
  const page = await createStealthPage(browser);

  await page.goto("https://www.reddit.com/login", { waitUntil: "networkidle2" });

  const info = await page.evaluate(() => {
    const inputs = Array.from(document.querySelectorAll("input")).map((i) => ({
      id: i.id,
      name: i.name,
      type: i.type,
      placeholder: i.placeholder?.slice(0, 30),
    }));
    const buttons = Array.from(document.querySelectorAll("button")).map((b) => ({
      text: b.textContent?.trim().slice(0, 30),
      type: b.type,
    }));
    const shadowInputs = [];
    document.querySelectorAll("*").forEach((el) => {
      if (el.shadowRoot) {
        el.shadowRoot.querySelectorAll("input").forEach((i) => {
          shadowInputs.push({ id: i.id, name: i.name, type: i.type, tag: el.tagName });
        });
      }
    });
    return { inputs, buttons, shadowInputs, url: window.location.href };
  });

  console.log("\n--- Reddit Login Page Debug ---");
  console.log("URL:", info.url);
  console.log("Inputs:", JSON.stringify(info.inputs, null, 2));
  console.log("Buttons:", JSON.stringify(info.buttons, null, 2));
  console.log("Shadow DOM inputs:", JSON.stringify(info.shadowInputs, null, 2));

  await ask("\nPress Enter to go to submit page...");
  await page.goto("https://www.reddit.com/r/test/submit", { waitUntil: "networkidle2" });

  const submitInfo = await page.evaluate(() => {
    const textareas = Array.from(document.querySelectorAll("textarea")).map((t) => ({
      placeholder: t.placeholder?.slice(0, 50),
      id: t.id,
    }));
    const buttons = Array.from(document.querySelectorAll("button")).map((b) => ({
      text: b.textContent?.trim().slice(0, 30),
    }));
    return { textareas, buttons, url: window.location.href };
  });

  console.log("\n--- Reddit Submit Page Debug ---");
  console.log("URL:", submitInfo.url);
  console.log("Textareas:", JSON.stringify(submitInfo.textareas, null, 2));
  console.log("Buttons:", JSON.stringify(submitInfo.buttons, null, 2));

  await ask("\nPress Enter to close...");
  rl.close();
  await browser.close();
})();
