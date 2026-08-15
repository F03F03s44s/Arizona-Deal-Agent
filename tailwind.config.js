/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        az: {
          copper: '#C86D3B',
          turquoise: '#30999B',
          sand: '#F7E7CE',
          sunset: '#E65C00',
          night: '#0B132B',
          canyon: '#8D3B1B',
          cactus: '#2D5A27',
          gold: '#FFB800'
        }
      }
    },
  },
  plugins: [],
};
