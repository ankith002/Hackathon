#!/usr/bin/env node
/**
 * Send email X (subject + body) to list Y (recipients)
 * X = data/email-draft.json
 * Y = data/recipients.txt (one email per line)
 *
 * Usage: npm run email:send
 *        npm run email:send -- --dry-run  (print only, don't send)
 */

import "dotenv/config";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { sendEmail } from "../lib/email.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DRAFT_FILE = path.join(__dirname, "..", "data", "email-draft.json");
const RECIPIENTS_FILE = path.join(__dirname, "..", "data", "recipients.txt");

const dryRun = process.argv.includes("--dry-run");

(async () => {
  if (!process.env.EMAIL_USER || !process.env.EMAIL_PASS) {
    console.error("❌ Set EMAIL_USER and EMAIL_PASS in .env (Gmail: use app password)");
    process.exit(1);
  }

  let draft, recipients;

  try {
    draft = JSON.parse(fs.readFileSync(DRAFT_FILE, "utf-8"));
  } catch (err) {
    console.error("❌ Could not read data/email-draft.json");
    process.exit(1);
  }

  try {
    const raw = fs.readFileSync(RECIPIENTS_FILE, "utf-8");
    recipients = raw
      .split("\n")
      .map((e) => e.trim().toLowerCase())
      .filter((e) => e && e.includes("@"));
  } catch (err) {
    console.error("❌ Could not read data/recipients.txt");
    process.exit(1);
  }

  if (recipients.length === 0) {
    console.error("❌ No valid emails in data/recipients.txt");
    process.exit(1);
  }

  console.log("\n📧 Email bulk send");
  console.log("   Subject:", draft.subject);
  console.log("   Recipients:", recipients.length);
  console.log("   Dry run:", dryRun);
  console.log("");

  if (dryRun) {
    recipients.forEach((to, i) => console.log(`   ${i + 1}. ${to}`));
    console.log("\n   Run without --dry-run to send.");
    return;
  }

  let sent = 0;
  let failed = 0;

  for (const to of recipients) {
    try {
      await sendEmail({
        to,
        subject: draft.subject,
        body: draft.body,
      });
      console.log(`   ✅ ${to}`);
      sent++;
    } catch (err) {
      console.error(`   ❌ ${to}: ${err.message}`);
      failed++;
    }
  }

  console.log(`\n   Done: ${sent} sent, ${failed} failed`);
})();
