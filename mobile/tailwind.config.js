/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: '#2563EB',     // Electric Blue
          slate: '#0F172A',    // Deep Slate
          teal: '#14B8A6',     // Teal Accent
        }
      }
    },
  },
  plugins: [],
}
