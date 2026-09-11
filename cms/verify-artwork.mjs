import path from "node:path";
import { chromium } from "playwright";

const ASSETS = path.resolve("../_given/assets");
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage();
page.on("pageerror", (err) => console.log("[pageerror]", err.message));

await page.goto("http://localhost:5173/login", { waitUntil: "networkidle" });
await page.fill("#email", "admin@peblo.test");
await page.fill("#password", "admin12345");
await page.click('button[type="submit"]');
await page.waitForURL("**/shows");
await page.waitForSelector("table.data-table");

await page.click("table.data-table tbody tr:first-child a");
await page.waitForSelector(".artwork-slots");

// Wrong-ratio upload -> expect inline rejection
const posterInput = page.locator(".artwork-slot", { hasText: "Poster" }).locator('input[type="file"]');
await posterInput.setInputFiles(path.join(ASSETS, "poster_wrong_ratio.jpg"));
await page.waitForSelector(".artwork-slot .field-error", { timeout: 10000 });
const errorText = await page.locator(".artwork-slot", { hasText: "Poster" }).locator(".field-error").innerText();
console.log("REJECTION MESSAGE:", errorText);
await page.screenshot({ path: "verify-shots/20-artwork-rejected.png" });

// Good upload -> expect success toast + preview image
await posterInput.setInputFiles(path.join(ASSETS, "poster_good.jpg"));
await page.waitForSelector(".toast-success", { timeout: 10000 });
const toastText = await page.locator(".toast-success").innerText();
console.log("SUCCESS TOAST:", toastText);
await page.screenshot({ path: "verify-shots/21-artwork-accepted.png" });

const previewSrc = await page.locator(".artwork-preview-poster").getAttribute("src");
console.log("preview src after success:", previewSrc);

await browser.close();
