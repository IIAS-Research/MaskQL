const { brand, accent } = require('./palette.json')

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand,
        accent,
      },
      ringColor: { DEFAULT: accent[200] },
    },
  },
  plugins: [],
}
