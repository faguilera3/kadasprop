/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f2f0fd',
          100: '#e8e2fb',
          200: '#d3c7f7',
          300: '#bda8f2',
          400: '#9d7bec',
          500: '#753ddb', // Base color
          600: '#6428ca',
          700: '#561eb0',
          800: '#481993',
          900: '#3c1678',
          950: '#250d53',
        }
      }
    },
  },
  plugins: [],
}
