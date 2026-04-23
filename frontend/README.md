# MrGrammar — Frontend

SvelteKit 2 + Svelte 5 + Tailwind CSS 4 + TypeScript frontend for the MrGrammar platform.

## Tech stack

| Technology | Version |
|------------|---------|
| SvelteKit | 2.57 |
| Svelte | 5 |
| Tailwind CSS | 4 |
| TypeScript | 6 |
| Vite | 8 |

## Development

Install dependencies and start the dev server:

```sh
npm install
npm run dev
```

The app expects the Django backend API to be available. Configure the URL via the `PUBLIC_API_URL` environment variable (defaults to `http://localhost:8000/api`). See `.env.example` in the project root.

## Type checking

```sh
npm run check
```

## Building

```sh
npm run build
npm run preview   # preview the production build locally
```
