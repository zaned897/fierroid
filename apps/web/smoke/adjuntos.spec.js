import { expect, test } from "./fixtures.js";

const org = "rancho-prueba";
const animals = [
  { org, tag_id: "MEDIA-001", alias: "La Pinta", readings: 0, has_photo: false },
  { org, tag_id: "MEDIA-002", alias: "La Colorada", readings: 0, has_photo: false },
];
const session = { id: "media-local", api_key: "token-local",
  user: { email: "media@example.test", full_name: "Ganadera de prueba", org, is_superuser: false } };

async function simulate(page, { loseAck = false, microphoneDenied = false, superuser = false } = {}) {
  await page.addInitScript(({ account, denied }) => {
    localStorage.setItem("fierro.session", JSON.stringify(account));
    window.__recordedTracks = [];
    // Fuente sintética; usa el MediaRecorder real del navegador para codificar.
    navigator.mediaDevices.getUserMedia = async () => {
      if (denied) throw new DOMException("Permiso denegado", "NotAllowedError");
      const audio = new AudioContext();
      const oscillator = audio.createOscillator();
      const output = audio.createMediaStreamDestination();
      oscillator.connect(output); oscillator.start();
      window.__recordedTracks.push(...output.stream.getTracks());
      return output.stream;
    };
  }, { account: { ...session, user: { ...session.user, is_superuser: superuser, org: superuser ? null : org } }, denied: microphoneDenied });
  const entries = new Map();
  const objects = new Map();
  const requests = { posts: [], uploads: [], reads: [] };
  let lost = false;
  const empty = (route) => route.fulfill({ json: { readings: [], next_cursor: null } });
  await page.route(/\/v1\/(?:animals\/[^/]+\/)?readings\?/, empty);
  await page.route(/\/v1\/devices$/, (route) => route.fulfill({ json: { devices: [] } }));
  await page.route(/\/v1\/animals$/, (route) => route.fulfill({ json: { animals } }));
  await page.route(/\/v1\/orgs$/, (route) => route.fulfill({ json: { orgs: [
    { slug: org, name: "Rancho de prueba" }, { slug: "otro-rancho", name: "Otro rancho" },
  ] } }));
  await page.route(/\/v1\/(?:animals\/[^/]+\/)?journal\?/, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const scope = url.searchParams.get("org");
    expect(request.headers().authorization).toBe(`Bearer ${session.api_key}`);
    expect(scope).toBeTruthy();
    const tag = url.pathname.match(/animals\/([^/]+)\//)?.[1];
    if (request.method() === "POST") {
      const data = request.postDataJSON();
      requests.posts.push(data);
      if (!entries.has(data.entry_id)) entries.set(data.entry_id, {
        ...data, org: scope, author: session.user.full_name, animals: data.animals || [tag],
        created_at: "2026-11-18T12:00:00Z", attachments: [],
      });
      await route.fulfill({ json: entries.get(data.entry_id) });
    } else await route.fulfill({ json: { entries: [...entries.values()]
      .filter((entry) => entry.org === scope && (!tag || entry.animals.includes(tag))), next_cursor: null } });
  });
  await page.route(/\/v1\/journal\/[^/]+\/attachments/, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    expect(request.headers().authorization).toBe(`Bearer ${session.api_key}`);
    const scope = url.searchParams.get("org");
    const [, entryId, id, content] = url.pathname.match(/journal\/([^/]+)\/attachments(?:\/([^/]+))?(?:\/(content))?$/);
    const entry = entries.get(entryId);
    if (!entry || entry.org !== scope) return route.fulfill({ status: 404, json: {} });
    if (request.method() === "POST") {
      const form = await new Response(request.postDataBuffer(), { headers: {
        "Content-Type": request.headers()["content-type"],
      } }).formData();
      const attachmentId = form.get("attachment_id");
      const file = form.get("file");
      const raw = Buffer.from(await file.arrayBuffer());
      const kind = form.get("kind");
      if (kind === "photo") expect([...raw.subarray(0, 3)]).toEqual([255, 216, 255]);
      else expect(file.type).toContain("audio/webm");
      requests.uploads.push(attachmentId);
      if (objects.has(attachmentId)) expect(objects.get(attachmentId).raw.equals(raw)).toBe(true);
      else {
        const item = { attachment_id: attachmentId, entry_id: entryId, kind,
          content_type: file.type.split(";")[0], byte_size: raw.length,
          duration_ms: kind === "audio" ? 1000 : null, created_at: "2026-11-18T12:00:00Z" };
        objects.set(attachmentId, { item, raw });
        entry.attachments.push(item);
      }
      if (loseAck && !lost && requests.uploads.length === 2) { lost = true; return route.abort("failed"); }
      return route.fulfill({ json: objects.get(attachmentId).item });
    }
    requests.reads.push({ org: scope, entryId, id });
    const stored = objects.get(id);
    if (content) return route.fulfill({ body: stored.raw, contentType: stored.item.content_type });
    return route.fulfill({ json: { url: `${url.pathname}/content?org=${scope}`, expires_at: "2099-01-01T00:00:00Z" } });
  });
  return { requests, entries, objects };
}

async function diary(page, superuser = false) {
  await page.getByRole("navigation", { name: "Secciones del panel" }).getByRole("button", { name: "Diario", exact: true }).click();
  if (superuser) await page.getByLabel("Organización del diario").selectOption(org);
}

async function form(page) {
  await page.getByRole("button", { name: "Nueva nota", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Nueva nota" });
  await dialog.getByRole("textbox", { name: "Nota", exact: true }).fill("Revisión del bebedero y de La Pinta.");
  await dialog.getByRole("checkbox", { name: /La Pinta/ }).check();
  return dialog;
}

async function photos(page, dialog, count = 2) {
  const bytes = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 1600; canvas.height = 900;
    const context = canvas.getContext("2d");
    context.fillStyle = "#176575"; context.fillRect(0, 0, 1600, 900);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  await dialog.getByLabel("Elegir fotos").setInputFiles(Array.from({ length: count }, (_, index) => ({
    name: `foto-${index}.png`, mimeType: "image/png", buffer: Buffer.from(bytes, "base64"),
  })));
  await expect(dialog.getByRole("img")).toHaveCount(count);
  await expect(dialog.getByRole("button", { name: "Nota de voz", exact: true })).toBeEnabled();
}

async function record(dialog) {
  await dialog.getByRole("button", { name: "Nota de voz", exact: true }).click();
  await expect(dialog.getByRole("timer")).toContainText("0:01");
  await dialog.getByRole("button", { name: "Detener grabación" }).click();
  await expect(dialog.locator("audio")).toHaveCount(1);
  await expect(dialog.getByRole("timer")).toHaveCount(0);
}

for (const width of [375, 1440]) {
  test(`guarda dos fotos y audio real, galería y teclado a ${width} px`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 1000 });
    const { requests, objects } = await simulate(page);
    await page.goto("/"); await diary(page);
    const dialog = await form(page);
    await photos(page, dialog); await record(dialog);
    expect(await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth)).toBe(true);
    await dialog.getByRole("button", { name: "Guardar nota" }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: `../../docs/design/diario/adjuntos-formulario-145-${width}.png` });
    await dialog.getByRole("button", { name: "Guardar nota" }).click();
    await expect(dialog).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Ampliar foto", exact: false })).toHaveCount(2);
    await expect(page.locator("audio")).toHaveCount(1);
    await expect.poll(() => new Set(requests.reads.map((request) => request.id)).size).toBe(3);
    for (const img of await page.locator(".journal-thumbnail img").all()) {
      await expect.poll(() => img.evaluate((node) => node.naturalWidth)).toBeGreaterThan(0);
    }
    expect(objects.size).toBe(3);
    expect(requests.posts).toHaveLength(1);
    expect(await page.evaluate(() => window.__recordedTracks.every((track) => track.readyState === "ended"))).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `../../docs/design/diario/adjuntos-galeria-145-${width}.png`, fullPage: true });
    const opener = page.getByRole("button", { name: "Ampliar foto 1 de la nota" });
    await opener.click();
    await expect(page.getByRole("dialog", { name: "Foto 1 de la nota" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(opener).toBeFocused();
    // La misma nota multimedia se ve en la ficha del animal.
    await page.getByRole("region", { name: "Notas del diario" }).getByRole("button", { name: "MEDIA-001", exact: true }).click();
    const bitacora = page.getByRole("region", { name: "Bitácora del animal" });
    await expect(bitacora.getByRole("button", { name: "Ampliar foto", exact: false })).toHaveCount(2);
    await expect(bitacora.locator("audio")).toHaveCount(1);
  });
}

test("recarga tras perder ACK de un adjunto y termina sin duplicar nota ni archivos", async ({ page }) => {
  const { requests, objects } = await simulate(page, { loseAck: true });
  await page.goto("/"); await diary(page);
  let dialog = await form(page);
  await photos(page, dialog); await record(dialog);
  await dialog.getByRole("button", { name: "Guardar nota" }).click();
  await expect(dialog.getByRole("alert")).toContainText("Conservamos el texto y los adjuntos");
  expect(objects.size).toBe(2);
  const initialIds = [...requests.uploads];
  await page.reload(); await diary(page);
  await page.getByRole("button", { name: "Nueva nota", exact: true }).click();
  dialog = page.getByRole("dialog", { name: "Nueva nota" });
  await expect(dialog.getByRole("textbox", { name: "Nota", exact: true })).toHaveValue("Revisión del bebedero y de La Pinta.");
  await expect(dialog.getByRole("img")).toHaveCount(2);
  await expect(dialog.locator("audio")).toHaveCount(1);
  await expect(dialog.getByRole("textbox", { name: "Nota", exact: true })).toBeDisabled();
  await dialog.getByRole("button", { name: "Reintentar adjuntos" }).click();
  await expect(dialog).toHaveCount(0);
  expect(requests.posts).toHaveLength(1);
  expect(objects.size).toBe(3);
  expect(requests.uploads.slice(2, 4)).toEqual(initialIds);
});

test("micrófono denegado permite quitar fotos y guardar texto con foto", async ({ page }) => {
  const { objects } = await simulate(page, { microphoneDenied: true });
  await page.goto("/"); await diary(page);
  const dialog = await form(page);
  await photos(page, dialog);
  await dialog.getByRole("button", { name: "Nota de voz", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("No hay permiso");
  await dialog.getByRole("button", { name: "Quitar foto 2", exact: true }).click();
  await expect(dialog.getByRole("img")).toHaveCount(1);
  await dialog.getByRole("button", { name: "Guardar nota" }).click();
  await expect(dialog).toHaveCount(0);
  expect(objects.size).toBe(1);
});

test("detiene sola la grabación antes del límite de dos minutos", async ({ page }) => {
  await simulate(page);
  await page.goto("/"); await diary(page);
  const dialog = await form(page);
  await page.clock.install();
  await dialog.getByRole("button", { name: "Nota de voz", exact: true }).click();
  await expect(dialog.getByRole("timer")).toContainText("0:01");
  await page.clock.fastForward(120000);
  await expect(dialog.getByRole("timer")).toHaveCount(0);
  await expect(dialog.locator("audio")).toHaveCount(1);
  expect(await page.evaluate(() => window.__recordedTracks.every((track) => track.readyState === "ended"))).toBe(true);
});

test("otra organización no recibe el borrador ni la galería del primer rancho", async ({ page }) => {
  const { requests } = await simulate(page, { superuser: true });
  await page.goto("/"); await diary(page, true);
  let dialog = await form(page);
  await photos(page, dialog, 1);
  await dialog.getByRole("button", { name: "Cerrar", exact: true }).click();
  await page.getByLabel("Organización del diario").selectOption("otro-rancho");
  await page.getByRole("button", { name: "Nueva nota", exact: true }).click();
  dialog = page.getByRole("dialog", { name: "Nueva nota" });
  await expect(dialog.getByRole("textbox", { name: "Nota", exact: true })).toBeEnabled();
  await expect(dialog.getByRole("textbox", { name: "Nota", exact: true })).toHaveValue("");
  await expect(dialog.getByRole("img")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Cerrar", exact: true }).click();
  await page.getByLabel("Organización del diario").selectOption(org);
  await page.getByRole("button", { name: "Nueva nota", exact: true }).click();
  dialog = page.getByRole("dialog", { name: "Nueva nota" });
  await expect(dialog.getByRole("img")).toHaveCount(1);
  await dialog.getByRole("button", { name: "Guardar nota" }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Ampliar foto 1 de la nota" })).toBeVisible();
  await page.getByLabel("Organización del diario").selectOption("otro-rancho");
  await expect(page.getByRole("button", { name: "Ampliar foto", exact: false })).toHaveCount(0);
  expect(requests.reads.every((request) => request.org === org)).toBe(true);
});
