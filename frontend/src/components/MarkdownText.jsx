import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

const MarkdownText = ({ text, className = '' }) => {
  if (!text) return null

  // Preprocess text to convert our specific format to markdown
  const preprocessText = (text) => {
    let processed = text

    // Convert section headers
    processed = processed.replace(/^Key Findings\s*\d+\./gm, '## Key Findings\n\n1.')
    processed = processed.replace(/^Evidence & Analysis\s*-/gm, '## Evidence & Analysis\n\n-')
    processed = processed.replace(/^Conclusions\s*[A-Z]/gm, '## Conclusions\n\n')
    processed = processed.replace(/^Follow-up Questions\s*\d+\./gm, '## Follow-up Questions\n\n1.')

    // Fix numbered lists that are concatenated
    processed = processed.replace(/(\d+\.\s+[^0-9]+?)(\d+\.\s+)/g, '$1\n\n$2')
    
    // Fix bullet points that are concatenated
    processed = processed.replace(/(-\s+[^-]+?)(-\s+)/g, '$1\n\n$2')

    // Add proper spacing between sections
    processed = processed.replace(/(## [A-Z][^#]+)/g, '\n\n$1\n\n')

    return processed
  }

  const processedText = preprocessText(text)

  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // Custom styling for different elements
          h1: ({ children }) => (
            <h1 className="text-2xl font-bold text-gray-900 mb-4 mt-4 border-b-2 border-blue-200 pb-2">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xl font-bold text-blue-600 mb-3 mt-4 border-b-2 border-blue-200 pb-2">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-lg font-semibold text-gray-800 mb-2 mt-3">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-base font-semibold text-gray-800 mb-2 mt-2">
              {children}
            </h4>
          ),
          p: ({ children }) => (
            <p className="text-gray-700 mb-3 leading-relaxed">
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside mb-3 space-y-1">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside mb-3 space-y-1">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-gray-700 ml-4">
              {children}
            </li>
          ),
          strong: ({ children }) => (
            <strong className="font-bold text-gray-900">
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em className="italic text-gray-800">
              {children}
            </em>
          ),
          code: ({ children, className }) => {
            const isInline = !className
            return isInline ? (
              <code className="bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-sm font-mono">
                {children}
              </code>
            ) : (
              <code className={`${className} block bg-gray-100 text-gray-800 p-3 rounded text-sm font-mono overflow-x-auto`}>
                {children}
              </code>
            )
          },
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-blue-300 pl-4 py-2 bg-blue-50 text-gray-700 italic mb-3">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto mb-3">
              <table className="min-w-full border border-gray-300">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-gray-50">
              {children}
            </thead>
          ),
          th: ({ children }) => (
            <th className="border border-gray-300 px-4 py-2 text-left font-semibold text-gray-900">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-gray-300 px-4 py-2 text-gray-700">
              {children}
            </td>
          ),
        }}
      >
        {processedText}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownText
