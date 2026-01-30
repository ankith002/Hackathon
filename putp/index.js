/**
 * Puppeteer Social Media Automation
 *
 * Usage:
 *   npm run save-cookies
 *   npm run post:reddit -- test "Title" "Body"
 *   npm run post:reddit:image -- test "Title" ./image.png
 */

export { launchBrowser, createStealthPage, randomDelay } from "./lib/browser.js";
export { loadCookies, saveCookies } from "./lib/cookies.js";
export { postToReddit, openReddit } from "./lib/platforms/reddit.js";
