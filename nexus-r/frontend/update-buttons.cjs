const fs = require('fs');
const files = [
  'AppearancePage.tsx',
  'GeneralPage.tsx',
  'MemoryPage.tsx',
  'ModelsPage.tsx',
  'PerformancePage.tsx',
  'ProvidersPage.tsx',
  'SettingsModal.tsx'
];

files.forEach(f => {
  const p = 'src/components/settings/' + f;
  let content = fs.readFileSync(p, 'utf8');
  let updated = content.replace(
    /className="px-8 py-2\.5 rounded-full text-sm font-bold bg-gray-900 text-white hover:bg-black dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200 shadow-md flex items-center gap-2 transition-all"/g,
    'className="px-8 py-2.5 rounded-full text-sm font-bold bg-slate-800 text-white hover:bg-slate-900 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200 shadow-md flex items-center gap-2 transition-all"'
  );
  if (content !== updated) {
    fs.writeFileSync(p, updated);
    console.log('Fixed ' + f);
  }
});
