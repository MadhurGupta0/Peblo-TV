import { chromium } from "playwright";

const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage();
page.on("console", (msg) => console.log(`[console.${msg.type()}]`, msg.text()));
page.on("pageerror", (err) => console.log("[pageerror]", err.message));
page.on("response", async (resp) => {
  if (resp.url().includes("localhost:8000")) {
    console.log(`[response] ${resp.status()} ${resp.request().method()} ${resp.url()}`);
  }
});

await page.goto("http://localhost:5173/login", { waitUntil: "networkidle" });
await page.fill("#email", "editor@peblo.test");
await page.fill("#password", "editor12345");
await page.click('button[type="submit"]');
await page.waitForTimeout(2000);
console.log("URL after login click + 2s:", page.url());
console.log("BODY TEXT:", (await page.locator("body").innerText()).slice(0, 500));
await page.screenshot({ path: "verify-shots/debug-after-login.png" });

await browser.close();
