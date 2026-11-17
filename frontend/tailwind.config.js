/** @type {import('tailwindcss').Config} */
// Zenfest brand: muted gold on warm black (see zenfestevents_webapp/DESIGN.md). Token names kept
// from the AI Hub so the shared building blocks read the same way.
module.exports = {
  content: ["./app/**/*.{js,jsx}", "./components/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        crt: "#0B0907", // page: warm near-black
        panel: "#14110D", // cards
        line: "#2A241C", // dividing lines
        phosphor: "#FBF7EE", // main text: jasmine ivory
        dim: "#A39886", // secondary text: warm taupe
        hazard: "#D9B24C", // the accent: the logo's muted gold (never brightened to yellow)
        signal: "#8FBF7F", // reserved for the "quote found" mark
      },
      fontFamily: {
        body: ["var(--font-body)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Impact", "sans-serif"],
      },
      borderRadius: {
        none: "0",
      },
    },
  },
  plugins: [],
};
