import { useState } from 'react';
import { Check, Copy, Download } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useEffect } from 'react';

interface CodeBlockProps {
  language: string;
  code: string;
}

export default function CodeBlock({ language, code }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    const checkDark = () => setIsDark(document.documentElement.classList.contains('dark'));
    checkDark();
    const observer = new MutationObserver(checkDark);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text', err);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `code.${language || 'txt'}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="my-4 rounded-xl overflow-hidden border border-gray-200 dark:border-[#333] bg-white dark:bg-[#1e1e1e] shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-[#2d2d2d] border-b border-gray-200 dark:border-[#333] text-xs text-gray-500 dark:text-gray-400">
        <span className="font-mono lowercase text-gray-600 dark:text-gray-300">{language || 'plaintext'}</span>
        <div className="flex items-center gap-3">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
          >
            {copied ? <Check size={14} className="text-green-600 dark:text-green-500" /> : <Copy size={14} />}
            {copied ? 'Copied!' : 'Copy'}
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
            title="Download code"
          >
            <Download size={14} />
          </button>
        </div>
      </div>
      
      {/* Code Content */}
      <div className="relative text-sm">
        <SyntaxHighlighter
          language={language || 'text'}
          style={isDark ? vscDarkPlus : vs}
          customStyle={{
            margin: 0,
            padding: '16px',
            background: 'transparent',
            fontSize: '14px',
            lineHeight: '1.5',
            overflowX: 'auto',
          }}
          PreTag="div"
          wrapLongLines={false}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
