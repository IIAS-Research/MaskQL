const { accent } = require('./palette.json')

const primaryColors = {
  '#3b82f6': accent[600],
  '#2563eb': accent[700],
  '#1d4ed8': accent[800],
  '#eff6ff': accent[50],
  '#bfdbfe': accent[200],
  '#9dc1fb': accent[300],
  '#70aeff': accent[500],
  '#696cff': accent[700],
  '#e9e9ff': accent[50],
}
const primaryRgb = accent[600].match(/[a-f\d]{2}/gi).map(hex => parseInt(hex, 16)).join(', ')

module.exports = {
  plugins: [
    {
      postcssPlugin: 'maskql-primevue-colors',
      // PrimeVue 3 embeds its primary colors in CSS, including hover and focus states.
      Declaration(declaration) {
        if (!declaration.source?.input.file?.endsWith('/lara-light-blue/theme.css')) return
        const shade = declaration.prop.match(/^--primary-(\d+)$/)?.[1]
        if (shade && accent[shade]) {
          declaration.value = accent[shade]
        } else if (!declaration.prop.startsWith('--blue-')) {
          declaration.value = declaration.value
            .replace(/#[a-f\d]{6}\b/gi, color => primaryColors[color.toLowerCase()] || color)
            .replace(/rgba\(59,\s*130,\s*246,/g, `rgba(${primaryRgb},`)
        }
      },
    },
    require('tailwindcss'),
    require('autoprefixer'),
  ],
}
