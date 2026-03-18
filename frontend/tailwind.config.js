/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f4ff',
          100: '#e0e9ff',
          200: '#c7d7fe',
          500: '#4f6ef7',
          600: '#3b55e6',
          700: '#2f45cc',
          800: '#2438a8',
          900: '#1a2b7a',
        }
      }
    }
  },
  plugins: []
}
