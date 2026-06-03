import colors from 'tailwindcss/colors.js';

const extractRGB = (hex) => {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `${r} ${g} ${b}`;
};

const palettes = {
  purple: colors.purple,
  blue: colors.blue,
  green: colors.emerald,
  orange: colors.orange,
  red: colors.red,
  pink: colors.pink,
};

const result = {};
for (const [name, palette] of Object.entries(palettes)) {
  result[name] = {};
  for (const [shade, hex] of Object.entries(palette)) {
    if (typeof hex === 'string' && hex.startsWith('#')) {
      result[name][shade] = extractRGB(hex);
    }
  }
}

console.log(JSON.stringify(result, null, 2));
