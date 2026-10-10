/**
 * Tailwind CSS v3 build config (build-time only — NOT shipped in the .exe).
 *
 * The app serves a pre-compiled, purged stylesheet from /static/css/tailwind.min.css.
 * Re-run this whenever you add/change Tailwind classes in index.html or app.js:
 *
 *   npx tailwindcss@3.4.17 -c tailwind.config.js -i tailwind.input.css -o static/css/tailwind.min.css --minify
 *
 * IMPORTANT: Tailwind only generates classes it can find as complete literal strings.
 * In app.js always write full class names (e.g. 'bg-emerald-500'), never build them
 * dynamically (e.g. `bg-${color}-500`).
 */
module.exports = {
  darkMode: 'class',
  content: ['./templates/**/*.html', './static/js/**/*.js'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
