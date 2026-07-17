const fs = require('fs');
const glob = require('glob');

const files = glob.sync('app/**/*.js');
const translations = new Map();

files.forEach(file => {
  const content = fs.readFileSync(file, 'utf8');
  const regex = /pick\(['"]([^'"]+)['"],\s*['"]([^'"]+)['"]\)/g;
  let match;
  while ((match = regex.exec(content)) !== null) {
    const ro = match[1];
    const en = match[2];
    translations.set(ro, en);
  }
});

console.log('Total unique translations:', translations.size);
fs.writeFileSync('translations.json', JSON.stringify(Object.fromEntries(translations), null, 2));