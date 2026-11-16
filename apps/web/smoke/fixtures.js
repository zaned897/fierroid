import { expect, test as base } from "@playwright/test";

// Las rutas específicas de cada prueba tienen prioridad sobre esta barrera.
export const test = base.extend({
  localOnly: [async ({ context, baseURL }, use) => {
    const unexpected = [];
    await context.route("**/*", async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.origin !== baseURL || url.pathname === "/v1" || url.pathname.startsWith("/v1/")) {
        unexpected.push(`${request.method()} ${url.href}`);
        await route.abort("blockedbyclient");
        return;
      }
      if (url.pathname === "/health") {
        await route.fulfill({ json: { ok: true, env: "local" } });
        return;
      }
      await route.continue();
    });
    await use();
    expect(unexpected, "Solicitudes externas o de API sin simular").toEqual([]);
  }, { auto: true }],
});

export { expect };
