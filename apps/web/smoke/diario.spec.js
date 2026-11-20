import { expect, test } from "./fixtures.js";

test.use({ timezoneId: "America/Mexico_City" });

const org = "rancho-prueba";
const animals = [
  { org, tag_id: "982000000000001", alias: "La Pinta", readings: 0, has_photo: false },
  { org, tag_id: "982000000000002", alias: "La Colorada", readings: 0, has_photo: false },
  { org: "otro-rancho", tag_id: "982000000000001", alias: "La Ajena", readings: 0, has_photo: false },
];
const session = {
  id: "diario-simulado", api_key: "token-local",
  user: { email: "diario@example.test", full_name: "Ganadera de prueba", org, is_superuser: false },
};
const previous = {
  entry_id: "10000000-0000-4000-8000-000000000001",
  body: "Nota anterior de la ficha. Vigilar la pata trasera.",
  category: "general", animals: [animals[0].tag_id], author: "Notas de la ficha",
  occurred_at: "2026-11-18T05:30:00.000Z", created_at: "2026-11-18T05:30:00.000Z",
};

async function simulate(page, { notes = [previous], loseAck = false, superuser = false, journalStatus } = {}) {
  const account = { ...session, user: { ...session.user, is_superuser: superuser, org: superuser ? null : org } };
  await page.addInitScript((value) => localStorage.setItem("fierro.session", JSON.stringify(value)), account);
  const entries = new Map(notes.map((entry) => [entry.entry_id, { ...entry, org }]));
  const requests = { posts: [], gets: [], aliases: [], questions: [] };
  const emptyReadings = (route) => route.fulfill({ json: { readings: [], next_cursor: null } });
  await page.route(/\/v1\/readings\?/, emptyReadings);
  await page.route(/\/v1\/animals\/[^/]+\/readings\?/, emptyReadings);
  await page.route(/\/v1\/devices$/, (route) => route.fulfill({ json: { devices: [] } }));
  await page.route(/\/v1\/animals$/, (route) => route.fulfill({ json: { animals: superuser ? animals : animals.filter((animal) => animal.org === org) } }));
  await page.route(/\/v1\/orgs$/, (route) => route.fulfill({ json: {
    orgs: [{ slug: org, name: "Rancho de prueba" }, { slug: "otro-rancho", name: "Otro rancho" }],
  } }));
  await page.route(/\/v1\/animals\/[^/?]+\?/, async (route) => {
    requests.aliases.push(route.request().postDataJSON());
    await route.fulfill({ json: {} });
  });
  await page.route(/\/v1\/asistente(?:\?|$)/, async (route) => {
    requests.questions.push({ url: route.request().url(), ...route.request().postDataJSON() });
    await route.fulfill({ json: { respuesta: "Consulta de prueba recibida.", aretes: [], consultas: [] } });
  });
  await page.route(/\/v1\/(?:animals\/[^/]+\/)?journal\?/, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const scope = url.searchParams.get("org");
    expect(scope).toBeTruthy();
    expect(request.headers().authorization).toBe(`Bearer ${account.api_key}`);
    if (!superuser) expect(scope).toBe(org);
    const animalTag = url.pathname.match(/\/animals\/([^/]+)\/journal/)?.[1];
    if (request.method() === "POST") {
      const content = request.postDataJSON();
      requests.posts.push({ org: scope, ...content });
      if (!entries.has(content.entry_id)) entries.set(content.entry_id, {
        ...content, org: scope, animals: content.animals || [animalTag],
        author: account.user.full_name, created_at: "2026-11-18T17:00:00.000Z",
      });
      if (loseAck && requests.posts.length === 1) return route.abort("failed");
      return route.fulfill({ json: entries.get(content.entry_id) });
    }
    requests.gets.push(url);
    if (journalStatus && !animalTag) return route.fulfill({ status: journalStatus, json: { detail: "Acceso de prueba rechazado." } });
    const tag = animalTag || url.searchParams.get("tag");
    const from = url.searchParams.get("desde");
    const to = url.searchParams.get("hasta");
    const matching = [...entries.values()].filter((entry) => entry.org === scope
      && (!tag || entry.animals.includes(tag))
      && (!from || entry.occurred_at >= from)
      && (!to || entry.occurred_at < to))
      .sort((a, b) => b.occurred_at.localeCompare(a.occurred_at) || b.entry_id.localeCompare(a.entry_id));
    const start = Number(url.searchParams.get("cursor") || 0);
    const size = Number(url.searchParams.get("limit") || 20);
    await route.fulfill({ json: {
      entries: matching.slice(start, start + size),
      next_cursor: matching.length > start + size ? String(start + size) : null,
    } });
  });
  return requests;
}

async function openDiary(page) {
  await page.getByRole("navigation", { name: "Secciones del panel" })
    .getByRole("button", { name: "Diario", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Diario", exact: true })).toBeVisible();
}

async function newNote(page, body) {
  await page.getByRole("button", { name: "Nueva nota", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Nueva nota" });
  await dialog.getByRole("textbox", { name: "Nota", exact: true }).fill(body);
  await dialog.getByLabel("Fecha del evento (hora local)").fill("2026-11-18T08:30");
  return dialog;
}

async function attachPhoto(page, dialog) {
  const bytes = await page.evaluate(async () => {
    const canvas = document.createElement("canvas");
    canvas.width = 4; canvas.height = 4;
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    return [...new Uint8Array(await blob.arrayBuffer())];
  });
  await dialog.getByLabel("Elegir fotos").setInputFiles({ name: "foto.png", mimeType: "image/png", buffer: Buffer.from(bytes) });
  await expect(dialog.getByRole("button", { name: "Quitar foto 1" })).toBeEnabled();
}

test("un adjunto rechazado se puede quitar tras recargar y nunca se reintenta", async ({ page }) => {
  const requests = await simulate(page);
  let uploads = 0;
  await page.route(/\/v1\/journal\/[^/]+\/attachments\?/, (route) => {
    uploads++;
    return route.fulfill({ status: 422, json: { detail: "Archivo inválido" } });
  });
  await page.goto("/");
  await openDiary(page);
  let dialog = await newNote(page, "Nota con foto rechazada.");
  await attachPhoto(page, dialog);
  await dialog.getByRole("button", { name: "Guardar nota" }).click();
  await expect(dialog.getByRole("alert")).toContainText("Adjunto rechazado");
  await expect(dialog.getByRole("button", { name: "Quitar foto 1" })).toBeEnabled();
  await expect(dialog.getByRole("button", { name: /Reintentar/ })).toHaveCount(0);
  await expect(dialog.getByRole("button", { name: "Completar nota" })).toBeDisabled();
  await page.reload();
  await openDiary(page);
  await page.getByRole("button", { name: "Nueva nota", exact: true }).click();
  dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("alert")).toContainText("Adjunto rechazado");
  await expect(dialog.getByRole("button", { name: /Reintentar/ })).toHaveCount(0);
  await dialog.getByRole("button", { name: "Quitar foto 1" }).click();
  await dialog.getByRole("button", { name: "Completar nota" }).click();
  await expect(dialog).toHaveCount(0);
  expect(uploads).toBe(1);
  expect(requests.posts).toHaveLength(1);
});

test("un fallo transitorio permite reintentar el adjunto sin duplicar la nota", async ({ page }) => {
  const requests = await simulate(page);
  let uploads = 0;
  await page.route(/\/v1\/journal\/[^/]+\/attachments\?/, (route) => {
    uploads++;
    return uploads === 1
      ? route.fulfill({ status: 503, json: { detail: "Temporal" } })
      : route.fulfill({ json: { attachment_id: "foto-confirmada", kind: "photo" } });
  });
  await page.goto("/");
  await openDiary(page);
  const dialog = await newNote(page, "Nota con envío temporalmente fallido.");
  await attachPhoto(page, dialog);
  await dialog.getByRole("button", { name: "Guardar nota" }).click();
  await expect(dialog.getByRole("button", { name: "Quitar foto 1" })).toBeEnabled();
  await dialog.getByRole("button", { name: "Reintentar adjuntos" }).click();
  await expect(dialog).toHaveCount(0);
  expect(uploads).toBe(2);
  expect(requests.posts).toHaveLength(1);
});

test("un borrador confirmado sin blobs recuperables se puede completar", async ({ page }) => {
  const requests = await simulate(page);
  await page.goto("/");
  await page.evaluate(async ({ account, entry }) => {
    const key = `fierro:bitacora:diario:${encodeURIComponent(account.user.email)}:${account.user.org}`;
    const db = await new Promise((resolve, reject) => {
      const request = indexedDB.open("fierro-journal-media", 1);
      request.onupgradeneeded = () => request.result.createObjectStore("drafts");
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    await new Promise((resolve, reject) => {
      const transaction = db.transaction("drafts", "readwrite");
      transaction.objectStore("drafts").put({
        body: entry.body, category: "general", occurred: "2026-11-18T08:30", animals: [],
        saved_at: Date.now(), confirmed: entry,
        files: [
          { attachment_id: "sin-datos", kind: "audio", status: "rejected" },
          { attachment_id: "url-vencida", kind: "photo", status: "uploading", file: "blob:ya-no-existe" },
        ],
      }, key);
      transaction.oncomplete = resolve;
      transaction.onerror = () => reject(transaction.error);
    });
    db.close();
  }, { account: session, entry: previous });
  await openDiary(page);
  await page.getByRole("button", { name: "Nueva nota", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("list", { name: "Adjuntos por guardar" })).toHaveCount(0);
  await dialog.getByRole("button", { name: "Completar nota" }).click();
  await expect(dialog).toHaveCount(0);
  expect(requests.posts).toHaveLength(0);
});

test("detener una grabación al instante avisa y no agrega ni sube audio", async ({ page }) => {
  const requests = await simulate(page);
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = async () => ({ getTracks: () => [{ stop() {} }] });
    window.MediaRecorder = class {
      static isTypeSupported() { return true; }
      state = "inactive";
      mimeType = "audio/webm";
      start() { this.state = "recording"; }
      stop() {
        this.state = "inactive";
        this.ondataavailable({ data: new Blob(["cabecera sin audio"]) });
        this.onstop();
      }
    };
  });
  await page.goto("/");
  await openDiary(page);
  const dialog = await newNote(page, "Nota sin audio vacío.");
  await dialog.getByRole("button", { name: "Nota de voz", exact: true }).click();
  await dialog.getByRole("button", { name: "Detener grabación" }).click();
  await expect(dialog.getByRole("alert")).toContainText("Graba al menos un segundo");
  await expect(dialog.getByRole("list", { name: "Adjuntos por guardar" })).toHaveCount(0);
  await dialog.getByRole("button", { name: "Guardar nota" }).click();
  await expect(dialog).toHaveCount(0);
  expect(requests.posts).toHaveLength(1);
});

test("guarda una nota del rancho en su día local y conserva la nota migrada", async ({ page }) => {
  const requests = await simulate(page);
  await page.goto("/");
  await openDiary(page);
  const day = page.getByRole("region", { name: /martes,? 17 de noviembre de 2026/i });
  await expect(day.getByText(previous.body)).toBeVisible();
  const dialog = await newNote(page, "Llovió en el potrero norte.");
  await dialog.getByLabel("Categoría").selectOption("clima");
  await dialog.getByRole("button", { name: "Guardar nota" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("status").filter({ hasText: "Nota guardada." })).toBeVisible();
  await expect(page.getByRole("region", { name: /miércoles,? 18 de noviembre de 2026/i })
    .getByText("Llovió en el potrero norte.")).toBeVisible();
  expect(requests.posts[0]).toMatchObject({
    org, animals: [], category: "clima", occurred_at: "2026-11-18T14:30:00.000Z",
  });
});

test("una nota de dos animales aparece en ambas fichas y el alias conserva el historial", async ({ page }) => {
  const requests = await simulate(page);
  await page.goto("/");
  await openDiary(page);
  const body = "Ambas pasaron al corral de observación.";
  const dialog = await newNote(page, body);
  await dialog.getByLabel("Buscar por arete o nombre").fill("Pinta");
  await dialog.getByRole("checkbox", { name: /La Pinta/ }).check();
  await dialog.getByLabel("Buscar por arete o nombre").fill("982000000000002");
  await dialog.getByRole("checkbox", { name: /La Colorada/ }).check();
  await dialog.getByRole("button", { name: "Guardar nota" }).click();
  await expect(dialog).toHaveCount(0);
  expect(requests.posts[0].animals).toEqual(animals.slice(0, 2).map((animal) => animal.tag_id));
  for (const animal of animals.slice(0, 2)) {
    const note = page.getByRole("region", { name: "Notas del diario" }).getByRole("listitem").filter({ has: page.getByText(body, { exact: true }) }).first();
    await note.getByRole("button", { name: animal.tag_id, exact: true }).click();
    await expect(page.getByRole("region", { name: "Bitácora del animal" }).getByText(body)).toBeVisible();
    await expect(page.getByRole("textbox", { name: "Notas", exact: true })).toHaveCount(0);
    if (animal === animals[0]) {
      await page.getByRole("textbox", { name: "Nombre", exact: true }).fill("La Pinta nueva");
      await page.getByRole("button", { name: "Guardar", exact: true }).click();
      await expect.poll(() => requests.aliases.length).toBe(1);
      expect(requests.aliases[0]).toEqual({ alias: "La Pinta nueva" });
      await expect(page.getByText(previous.body)).toBeVisible();
    }
    await page.getByRole("button", { name: "Ver en el diario" }).click();
    await expect(page.getByLabel("Animal", { exact: true })).toHaveValue(animal.tag_id);
    await expect(page.getByText(body, { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Limpiar filtros" }).click();
  }
});

test("recupera borrador, selección y UUID tras perder la respuesta y recargar", async ({ page }) => {
  const requests = await simulate(page, { loseAck: true });
  await page.goto("/");
  await openDiary(page);
  const body = "Aplicamos vacuna a las dos vacas.";
  let dialog = await newNote(page, body);
  await dialog.getByRole("checkbox", { name: /La Pinta/ }).check();
  await dialog.getByRole("checkbox", { name: /La Colorada/ }).check();
  await dialog.getByLabel("Categoría").selectOption("salud");
  await dialog.getByRole("button", { name: "Guardar nota" }).click();
  await expect(dialog.getByRole("alert")).toContainText("No se confirmó el guardado");
  const first = requests.posts[0];
  await page.reload();
  await openDiary(page);
  await page.getByRole("button", { name: "Nueva nota", exact: true }).click();
  dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("textbox", { name: "Nota", exact: true })).toHaveValue(body);
  await expect(dialog.getByRole("checkbox", { name: /La Pinta/ })).toBeChecked();
  await expect(dialog.getByRole("checkbox", { name: /La Colorada/ })).toBeChecked();
  await expect(dialog.getByLabel("Categoría")).toHaveValue("salud");
  await dialog.getByRole("button", { name: "Guardar nota" }).click();
  await expect(page.getByText("Nota guardada.", { exact: true })).toBeVisible();
  expect(requests.posts).toEqual([first, first]);
  await expect(page.getByText(body, { exact: true })).toHaveCount(1);
});

test("filtra categorías recorriendo páginas y convierte el rango local a UTC", async ({ page }) => {
  const notes = Array.from({ length: 21 }, (_, index) => ({
    ...previous, entry_id: `10000000-0000-4000-8000-${String(index + 10).padStart(12, "0")}`,
    body: `Evento ${index}`, category: index === 0 ? "salud" : "clima",
    occurred_at: `2026-11-18T${String(12 + Math.floor(index / 5)).padStart(2, "0")}:${String(index % 5).padStart(2, "0")}:00.000Z`,
  }));
  const requests = await simulate(page, { notes });
  await page.goto("/");
  await openDiary(page);
  await page.getByLabel("Desde", { exact: true }).fill("2026-11-18");
  await page.getByLabel("Hasta", { exact: true }).fill("2026-11-18");
  await page.getByLabel("Animal", { exact: true }).selectOption(animals[0].tag_id);
  await page.getByLabel("Categoría", { exact: true }).selectOption("salud");
  await page.getByRole("button", { name: "Aplicar filtros" }).click();
  await expect(page.getByText("Evento 0", { exact: true })).toBeVisible();
  await expect(page.getByText("Evento 20", { exact: true })).toHaveCount(0);
  expect(requests.gets.some((url) => url.searchParams.get("cursor") === "20")).toBe(true);
  const query = requests.gets.at(-1).searchParams;
  expect(query.get("desde")).toBe("2026-11-18T06:00:00.000Z");
  expect(query.get("hasta")).toBe("2026-11-19T06:00:00.000Z");
  expect(query.get("tag")).toBe(animals[0].tag_id);
});

test("lleva el contexto al asistente y espera a que el usuario envíe la pregunta", async ({ page }) => {
  const requests = await simulate(page);
  await page.goto("/");
  await openDiary(page);
  await page.getByLabel("Desde", { exact: true }).fill("2026-11-17");
  await page.getByLabel("Animal", { exact: true }).selectOption(animals[0].tag_id);
  await page.getByRole("button", { name: "Aplicar filtros" }).click();
  await page.getByRole("button", { name: "Pregúntale a tu hato" }).click();
  await expect(page.getByRole("textbox", { name: "Escribe tu pregunta" })).toHaveValue(
    `¿Qué información tienes del animal con arete ${animals[0].tag_id} desde el 2026-11-17?`,
  );
  expect(requests.questions).toHaveLength(0);
  await page.getByRole("button", { name: "Enviar", exact: true }).click();
  await expect(page.getByText("Consulta de prueba recibida.")).toBeVisible();
  expect(new URL(requests.questions[0].url).searchParams.get("org")).toBe(org);
});

test("el superusuario elige organización y cada una conserva su propio borrador", async ({ page }) => {
  const requests = await simulate(page, { superuser: true });
  await page.goto("/");
  await openDiary(page);
  await expect(page.getByRole("button", { name: "Nueva nota", exact: true })).toHaveCount(0);
  await page.getByLabel("Organización del diario").selectOption(org);
  let dialog = await newNote(page, "Borrador del primer rancho.");
  await expect(dialog.getByRole("checkbox", { name: /La Ajena/ })).toHaveCount(0);
  await dialog.getByRole("checkbox", { name: /La Pinta/ }).check();
  await page.keyboard.press("Escape");
  await page.getByLabel("Organización del diario").selectOption("otro-rancho");
  await page.getByRole("button", { name: "Nueva nota", exact: true }).click();
  dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("textbox", { name: "Nota", exact: true })).toHaveValue("");
  await expect(dialog.getByRole("checkbox", { name: /La Ajena/ })).toBeVisible();
  await dialog.getByRole("button", { name: "Cerrar", exact: true }).click();
  await page.getByLabel("Organización del diario").selectOption(org);
  await page.getByRole("button", { name: "Nueva nota", exact: true }).click();
  dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("textbox", { name: "Nota", exact: true })).toHaveValue("Borrador del primer rancho.");
  await expect(dialog.getByRole("checkbox", { name: /La Pinta/ })).toBeChecked();
  await dialog.getByRole("button", { name: "Guardar nota" }).click();
  await expect(page.getByText("Nota guardada.", { exact: true })).toBeVisible();
  expect(requests.posts[0].org).toBe(org);
});

test("muestra el rechazo de acceso y permite reintentar la consulta", async ({ page }) => {
  await simulate(page, { journalStatus: 403 });
  await page.goto("/");
  await openDiary(page);
  await expect(page.getByRole("alert")).toContainText("No se pudieron cargar las notas");
  await expect(page.getByText(previous.body)).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Actualizar diario" })).toBeEnabled();
});

for (const width of [375, 1440]) {
  test(`diario y nueva nota a ${width} px sin desbordamiento y con cierre por teclado`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 1000 });
    await simulate(page);
    await page.goto("/");
    await openDiary(page);
    await expect(page.getByText(previous.body)).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `../../docs/design/diario/diario-150-${width}.png`, fullPage: true });
    const dialog = await newNote(page, "El equipo revisó los bebederos.");
    await dialog.getByLabel("Categoría").selectOption("equipo");
    await dialog.getByRole("checkbox", { name: /La Pinta/ }).check();
    expect(await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth)).toBe(true);
    await page.screenshot({ path: `../../docs/design/diario/nueva-nota-150-${width}.png` });
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Nueva nota", exact: true })).toBeFocused();
  });
}
