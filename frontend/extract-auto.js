const fs = require('fs');
const content = fs.readFileSync('app/components/AutomaticPageTranslation.js', 'utf8');
const translations = new Map();

const regex = /"([^"]+)"\s*:\s*"([^"]+)"/g;
let match;
while ((match = regex.exec(content)) !== null) {
  const ro = match[1];
  const en = match[2];
  if (!ro.includes('\\')) {
    translations.set(ro, en);
  }
}

console.log('Total:', translations.size);
fs.writeFileSync('auto-translations.json', JSON.stringify(Object.fromEntries(translations), null, 2));