# Onboarding: colaborar en Fierro

Para quien llega nuevo y no programa. Pide los cambios a Claude Code (en claude.ai o en tu PC): él programa, prueba y abre el PR; tú revisas la preview y `zaned897` revisa y fusiona.

Tutorial general (cuentas, Claude Code, Projects y flujo de PR): https://claude.ai/artifact/LQf8v6yuNDkx7EaTfVywEv

## Qué es este repo
Pesaje de ganado: asocia el arete RFID de cada animal con su peso, lo guarda en la estación (Raspberry Pi) y lo sube a la nube. Detalle en [`README.md`](README.md).
| Parte | Carpeta | Qué hace |
|---|---|---|
| Estación | `apps/device-agent` | Lee arete y báscula, guarda y sincroniza. Fuera de la RPi corre simulada (`FIERRO_MOCK_HW=1`) |
| API | `apps/api` | Recibe los pesajes (Python, FastAPI) |
| App web | `apps/web` | La PWA que ve el ganadero en el celular (React) |

Regla raíz: **ninguna lectura de pesaje se pierde**, y nunca se inventa un peso.

## Requisitos
| Para | Necesitas |
|---|---|
| Pedir cambios y ver previews | Cuenta de GitHub como colaborador del repo y cuenta de Claude. Nada más |
| Levantar solo la app web | Git y [Node 22](https://nodejs.org) (trae `corepack`, que instala pnpm solo) |
| Levantar API y base de datos | Además [Docker Desktop](https://www.docker.com/products/docker-desktop/) (recomendado en Windows) o Python 3.12 (Mac) |
| Revisar un PR en local | Además GitHub CLI (`gh`) con `gh auth login` hecho |

## Levantar en local
En Windows usa **Git Bash**.
```bash
gh repo clone zaned897/fierroid
cd fierroid
cp .env.example .env
```
**Solo la app web** (suficiente para textos y pantallas):
```bash
cd apps/web
corepack pnpm install
corepack pnpm dev
```
Abre http://localhost:5173. Sin la API, el inicio se ve completo y el login dice que no pudo contactarla; eso es lo esperado.

**Con API y base de datos** (en otra terminal, desde la raíz del repo):
```bash
docker compose up -d db api       # Postgres + API en http://localhost:8000
docker compose --profile mock up -d agent   # opcional: estación simulada que genera pesajes
docker compose down               # para apagar todo
```
En Mac sin Docker: `./scripts/install-deps.sh && source .venv/bin/activate` y sigue la sección «Correr en local» del README.

## Ver la preview de un PR
Vercel publica la app web de cada PR en una liga temporal; la deja como comentario del bot de Vercel o en los checks del PR. Las previews usan la API de **stage** (datos sintéticos), nunca producción. El login con Google puede no funcionar en la liga de preview; para probar algo con sesión, avísale al dueño.
Si tu PR no muestra preview, no es error tuyo: el plan gratuito de Vercel puede bloquear commits de personas fuera del equipo. Avísale al dueño en el PR.

## Revisar un PR en local
```bash
gh pr checkout 123                # baja la rama del PR 123
cd apps/web && corepack pnpm install && corepack pnpm dev
git switch main && git pull       # para volver a la versión buena
```

## Primer PR
Empieza por una issue con `good first issue` o la que te asigne el dueño. Buenos primeros cambios: textos de la app web y documentación. En un hilo nuevo de Claude:
> Quiero resolver esta issue: <liga>. No programo. Explícame en 3 líneas qué vas a cambiar y dónde se verá; cuando te diga que sí, hazlo en una rama, corre las pruebas que pide CLAUDE.md y abre un PR con la plantilla.

## No tocar sin el dueño
- `apps/device-agent`, drivers serial, `deploy/` y `hardware/`: corren en el rancho y pueden perder pesajes.
- `infra/` (Terraform crea recursos que se cobran) y `apps/web/vercel.json`.
- Ramas `stage` y `production`: solo se promueven desde `main`, nunca se tocan directo.
- Llaves (`.env`, Google, Anthropic): nunca en el repo ni en el chat.

## Instrucciones de proyecto para claude.ai
Pega esto en las instrucciones de tu proyecto (un proyecto por repo):
```text
Repo: zaned897/fierroid, pesaje de ganado (estación RPi, API y app web). Soy colaborador y no programo: explícame en español claro, sin jerga, y sigue la skill onboarding, ONBOARDING.md y CLAUDE.md del repo.
Antes de cambiar código, dime en 3 líneas qué vas a hacer y espera mi sí. Trabaja en una rama nueva, un PR pequeño por issue contra main, con la plantilla del repo y la liga de la preview de Vercel. Siempre FIERRO_MOCK_HW=1: nunca hardware real.
Nunca apruebes ni fusiones PRs, ni empujes a main, stage o production: eso lo hace zaned897. Nunca me pidas llaves ni contraseñas. Si algo se atora tras 3 intentos, usa la skill fierro-unblock y dime qué bloquea.
```
