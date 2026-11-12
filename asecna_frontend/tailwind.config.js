/**
 * Tailwind 4 se configure depuis le CSS.
 *
 * Ce fichier dupliquait la palette `asecna` alors qu'il n'est jamais chargé :
 * en v4, `tailwind.config.js` n'est lu que si une directive `@config` le
 * désigne depuis la feuille de styles, ce qui n'est pas le cas ici. Les deux
 * définitions ont divergé sans que rien ne le signale.
 *
 * La seule source de vérité est le bloc `@theme` de `src/index.css`.
 *
 * @type {import('tailwindcss').Config}
 */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
}
