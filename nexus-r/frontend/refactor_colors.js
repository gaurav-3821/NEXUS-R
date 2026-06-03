import fs from 'fs';
import path from 'path';

const walk = (dir, callback) => {
  fs.readdirSync(dir).forEach(f => {
    let dirPath = path.join(dir, f);
    let isDirectory = fs.statSync(dirPath).isDirectory();
    isDirectory ? walk(dirPath, callback) : callback(path.join(dir, f));
  });
};

walk('./src', (filePath) => {
  if (filePath.endsWith('.tsx') || filePath.endsWith('.ts') || filePath.endsWith('.css')) {
    let content = fs.readFileSync(filePath, 'utf8');
    let original = content;

    // Replace specific tailwind arbitrary values
    content = content.replace(/bg-\[#4f46e5\]/g, 'bg-accent-600');
    content = content.replace(/text-\[#4f46e5\]/g, 'text-accent-600');
    content = content.replace(/border-\[#4f46e5\]/g, 'border-accent-600');
    
    // Replace standard indigo palette shades with accent
    content = content.replace(/\bindigo-50\b/g, 'accent-50');
    content = content.replace(/\bindigo-100\b/g, 'accent-100');
    content = content.replace(/\bindigo-200\b/g, 'accent-200');
    content = content.replace(/\bindigo-300\b/g, 'accent-300');
    content = content.replace(/\bindigo-400\b/g, 'accent-400');
    content = content.replace(/\bindigo-500\b/g, 'accent-500');
    content = content.replace(/\bindigo-600\b/g, 'accent-600');
    content = content.replace(/\bindigo-700\b/g, 'accent-700');
    content = content.replace(/\bindigo-800\b/g, 'accent-800');
    content = content.replace(/\bindigo-900\b/g, 'accent-900');

    if (content !== original) {
      fs.writeFileSync(filePath, content, 'utf8');
      console.log('Updated ' + filePath);
    }
  }
});
