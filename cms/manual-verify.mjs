import { chromium } from "playwright";

const consoleErrors = [];
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage();
page.on("console", (msg) => {
  if (msg.type() === "error") consoleErrors.push(msg.text());
});
page.on("pageerror", (err) => consoleErrors.push(`pageerror: ${err.message}`));

async function shot(name) {
  await page.screenshot({ path: `verify-shots/${name}.png` });
  console.log(`screenshot: ${name}`);
}

try {
  await page.goto("http://localhost:5173/login", { waitUntil: "networkidle" });
  await shot("01-login");

  await page.fill("#email", "editor@peblo.test");
  await page.fill("#password", "editor12345");
  await page.click('button[type="submit"]');
  await page.waitForURL("**/shows");
  await page.waitForSelector("table.data-table");
  await shot("02-shows-list-editor");

  // filters reflected in URL
  await page.selectOption('select:below(:text("Section"))', "series").catch(() => {});
  const sectionSelect = page.locator("label", { hasText: "Section" }).locator("select");
  await sectionSelect.selectOption("series");
  await page.waitForTimeout(400);
  console.log("url after section filter:", page.url());
  await shot("03-shows-filtered-series");

  const statusSelect = page.locator("label", { hasText: "Status" }).locator("select");
  await statusSelect.selectOption("published");
  await page.waitForTimeout(400);
  console.log("url after status filter:", page.url());
  await shot("04-shows-filtered-status");

  const searchInput = page.locator("label", { hasText: "Search" }).locator("input");
  await searchInput.fill("Moti");
  await page.waitForTimeout(500);
  console.log("url after search:", page.url());
  await shot("05-shows-filtered-search");

  // clear filters, click into a show
  await page.goto("http://localhost:5173/shows");
  await page.waitForSelector("table.data-table");
  await page.click("table.data-table tbody tr:first-child a");
  await page.waitForSelector(".entity-form");
  await shot("06-show-detail");

  const titleInput = page.locator("#title");
  const originalTitle = await titleInput.inputValue();
  await titleInput.fill(originalTitle + " (edited)");
  await page.click('.entity-form button[type="submit"]');
  await page.waitForSelector(".toast-success");
  await shot("07-show-saved-toast");

  // artwork upload UI present
  await page.waitForSelector(".artwork-slots");
  const artworkLabels = await page.locator(".artwork-slot-label").allTextContents();
  console.log("artwork slot labels:", artworkLabels);
  await shot("08-artwork-slots");

  // publish page as editor
  await page.click('a:has-text("Publish")');
  await page.waitForSelector("h1:has-text('Publish')");
  await page.waitForTimeout(800);
  await shot("09-publish-page-editor");
  const permDeniedVisible = await page.locator(".state-denied").isVisible().catch(() => false);
  const publishBtnDisabledEditor = await page.locator("button:has-text('Publish catalogue')").isDisabled();
  console.log("editor sees permission-denied panel:", permDeniedVisible);
  console.log("publish button disabled for editor:", publishBtnDisabledEditor);

  // log out, log in as admin
  await page.click('button:has-text("Log out")');
  await page.waitForURL("**/login");
  await shot("10-login-again");

  await page.fill("#email", "admin@peblo.test");
  await page.fill("#password", "admin12345");
  await page.click('button[type="submit"]');
  await page.waitForURL("**/shows");

  await page.click('a:has-text("Publish")');
  await page.waitForSelector("h1:has-text('Publish')");
  await page.waitForTimeout(800);
  await shot("11-publish-page-admin");
  const publishBtnDisabledAdmin = await page.locator("button:has-text('Publish catalogue')").isDisabled();
  const hint = await page.locator(".hint").allTextContents().catch(() => []);
  console.log("publish button disabled for admin:", publishBtnDisabledAdmin);
  console.log("hints on publish page:", hint);

  console.log("CONSOLE ERRORS:", JSON.stringify(consoleErrors, null, 2));
} catch (err) {
  console.error("SCRIPT FAILED:", err);
  await shot("ERROR-state");
  console.log("CONSOLE ERRORS SO FAR:", JSON.stringify(consoleErrors, null, 2));
  process.exitCode = 1;
} finally {
  await browser.close();
}
