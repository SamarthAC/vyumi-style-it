import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function portrait(page: Page, size = 600) {
  const data = await page.evaluate((size) => {
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#a89980";
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = "#426d60";
    ctx.fillRect(size / 4, size / 4, size / 2, size / 2);
    return canvas.toDataURL("image/png").split(",")[1];
  }, size);
  return {
    name: "portrait.png",
    mimeType: "image/png",
    buffer: Buffer.from(data, "base64"),
  };
}

async function demo(page: Page) {
  await page.goto("/");
  await page.getByRole("switch", { name: "Demo mode" }).click();
  await expect(
    page.getByText("Demo collection", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".product-card")).toHaveCount(6);
}

test("real backend catalog, filters, search, sorting and persistent saved pieces", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByText("Live collection", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".product-card")).toHaveCount(6);
  await page.getByRole("button", { name: "Dresses 2", exact: true }).click();
  await expect(page.locator(".product-card")).toHaveCount(2);
  await page.getByRole("button", { name: "All pieces 6", exact: true }).click();
  await page.getByRole("textbox", { name: "Search pieces" }).fill("denim");
  await expect(page.locator(".product-card")).toHaveCount(1);
  await page
    .getByRole("button", {
      name: "Save Casual Denim Western Shirt",
      exact: true,
    })
    .click();
  await page.getByRole("button", { name: "Clear search" }).click();
  await page
    .getByRole("combobox", { name: "Sort pieces" })
    .selectOption("name");
  await expect(page.locator(".product-card h3").first()).toContainText("Boho");
  await page.reload();
  await page.getByRole("button", { name: "Saved1 pieces" }).click();
  await expect(page.locator(".product-card")).toHaveCount(1);
  await expect(page.locator(".product-card h3")).toContainText("Denim");
  await page
    .getByRole("button", {
      name: "Unsave Casual Denim Western Shirt",
      exact: true,
    })
    .click();
  await expect(page.getByText("Keep a little inspiration.")).toBeVisible();
});

test("demo completes a labeled flow, comparison and download without uploading", async ({
  page,
}) => {
  const uploads: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/style-it/upload")) uploads.push(request.url());
  });
  await demo(page);
  await page
    .getByRole("button", {
      name: "Try on Classic White Linen Shirt",
      exact: true,
    })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: /Use a demo portrait/ }).click();
  await dialog
    .getByRole("button", { name: "Explore a reference look" })
    .click();
  await expect(
    dialog.getByText(
      "This reference is not generated from your photo or selected garment.",
    ),
  ).toBeVisible();
  await dialog
    .getByRole("button", { name: "Demo portrait", exact: true })
    .click();
  await expect(dialog.locator(".sample-original")).toBeVisible();
  await dialog
    .getByRole("button", { name: "Reference result", exact: true })
    .click();
  const download = page.waitForEvent("download");
  await dialog
    .getByRole("button", { name: "Download reference sheet" })
    .click();
  expect((await download).suggestedFilename()).toBe(
    "vyumi-reference-sheet.png",
  );
  expect(uploads).toHaveLength(0);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
});

test("image validation rejects invalid files and accepts a personal demo upload", async ({
  page,
}) => {
  await demo(page);
  await page
    .getByRole("button", {
      name: "Try on Classic White Linen Shirt",
      exact: true,
    })
    .click();
  const upload = page.getByLabel("Upload portrait");
  await upload.setInputFiles({
    name: "notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("hello"),
  });
  await expect(page.getByRole("alert")).toContainText("JPEG, PNG, or WebP");
  await upload.setInputFiles({
    name: "fake.png",
    mimeType: "image/png",
    buffer: Buffer.from("not a real image"),
  });
  await expect(page.getByRole("alert")).toContainText("couldn’t be read");
  await upload.setInputFiles(await portrait(page, 200));
  await expect(page.getByRole("alert")).toContainText("512 pixels");
  await upload.setInputFiles({
    name: "large.png",
    mimeType: "image/png",
    buffer: Buffer.alloc(10 * 1024 * 1024 + 1),
  });
  await expect(page.getByRole("alert")).toContainText("larger than 10 MB");
  await upload.setInputFiles(await portrait(page));
  await expect(page.getByAltText("Your uploaded portrait")).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.getByRole("button", { name: "Explore a reference look" }).click();
  await expect(
    page.getByRole("button", { name: "Your photo", exact: true }),
  ).toBeVisible();
});

test("unavailable engine is explained and cannot submit a real generation", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", {
      name: "Try on Classic White Linen Shirt",
      exact: true,
    })
    .click();
  await page.getByLabel("Upload portrait").setInputFiles(await portrait(page));
  await expect(
    page.getByRole("button", { name: "Create my look" }),
  ).toBeDisabled();
  await expect(
    page
      .getByText("Virtual try-on is currently offline.", { exact: false })
      .last(),
  ).toBeVisible();
});

test("connected generation sends real upload, polls and displays the result", async ({
  page,
}) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({
      json: { status: "healthy", engine_ready: true, product_count: 6 },
    }),
  );
  let submitted: { user_image_id: string; product_id: string } | null = null;
  await page.route("**/api/style-it/generate", (route) => {
    submitted = route.request().postDataJSON();
    return route.fulfill({
      status: 202,
      json: { job_id: "browser-job", status: "pending" },
    });
  });
  let polls = 0;
  await page.route("**/api/style-it/jobs/browser-job", (route) =>
    route.fulfill({
      json:
        ++polls < 2
          ? { status: "processing" }
          : {
              status: "completed",
              result_image_url: "/products/prod_shirt_classic_white/image",
            },
    }),
  );
  await page.goto("/");
  await page
    .getByRole("button", {
      name: "Try on Classic White Linen Shirt",
      exact: true,
    })
    .click();
  await page.getByLabel("Upload portrait").setInputFiles(await portrait(page));
  await page.getByRole("button", { name: "Create my look" }).click();
  await expect(
    page.getByAltText(
      "Your generated try-on wearing Classic White Linen Shirt",
    ),
  ).toBeVisible();
  expect(submitted!.product_id).toBe("prod_shirt_classic_white");
  expect(submitted!.user_image_id).toMatch(/^[a-f0-9]{32}$/);
  expect(polls).toBe(2);
  await page.getByRole("button", { name: "Your photo", exact: true }).click();
  await expect(
    page.getByAltText("Your original uploaded portrait"),
  ).toBeVisible();
});

test("generation failure returns to upload with an actionable message", async ({
  page,
}) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({
      json: { status: "healthy", engine_ready: true, product_count: 6 },
    }),
  );
  await page.route("**/api/style-it/generate", (route) =>
    route.fulfill({
      status: 503,
      json: {
        detail: "The try-on service is unavailable. Please try again later.",
      },
    }),
  );
  await page.goto("/");
  await page
    .getByRole("button", {
      name: "Try on Classic White Linen Shirt",
      exact: true,
    })
    .click();
  await page.getByLabel("Upload portrait").setInputFiles(await portrait(page));
  await page.getByRole("button", { name: "Create my look" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "try-on service is unavailable",
  );
  await expect(page.getByAltText("Your uploaded portrait")).toBeVisible();
});

test("offline catalog offers working retry and demo fallback", async ({
  page,
}) => {
  await page.route("**/api/products", (route) =>
    route.fulfill({ status: 502, body: "Bad gateway" }),
  );
  await page.goto("/");
  await expect(page.getByText("The studio is taking a moment.")).toBeVisible();
  await page.getByRole("button", { name: "Try again", exact: true }).click();
  await expect(page.getByText("The studio is taking a moment.")).toBeVisible();
  await page.getByRole("button", { name: "Explore demo", exact: true }).click();
  await expect(page.locator(".product-card")).toHaveCount(6);
});

test("mobile layout, navigation and modal stay within the viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await demo(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page
    .getByRole("button", { name: "How it works", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("dialog", { name: "How VYUMI works" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", {
      name: "Try on Classic White Linen Shirt",
      exact: true,
    })
    .click();
  const box = await page.getByRole("dialog").boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  expect(box!.height).toBeLessThanOrEqual(844);
  await page.getByRole("button", { name: "Close dialog" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("catalog and demo studio have no automated WCAG A/AA violations", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await demo(page);
  const check = async () => {
    await page.evaluate(() =>
      document.getAnimations().forEach((animation) => animation.finish()),
    );
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(result.violations).toEqual([]);
  };
  await check();
  await page
    .getByRole("button", {
      name: "Try on Classic White Linen Shirt",
      exact: true,
    })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await check();
  await page.getByRole("button", { name: /Use a demo portrait/ }).click();
  await page.getByRole("button", { name: "Explore a reference look" }).click();
  await expect(
    page.getByRole("button", { name: "Download reference sheet" }),
  ).toBeVisible();
  await check();
});
