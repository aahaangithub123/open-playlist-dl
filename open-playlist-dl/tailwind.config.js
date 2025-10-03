/** @type {import('tailwindcss').Config} */
export default {
  // Ensure the glob patterns are correct and enclosed in double quotes.
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}", // <--- Check this line carefully
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}