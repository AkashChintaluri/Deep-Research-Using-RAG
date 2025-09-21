import { useState } from 'react'
import MarkdownText from './MarkdownText'

const PaperDetail = ({ paper, isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState('overview')

  if (!isOpen || !paper) return null

  const getScoreColor = (score) => {
    if (score >= 0.8) return 'text-green-600 bg-green-50 border-green-200'
    if (score >= 0.6) return 'text-yellow-600 bg-yellow-50 border-yellow-200'
    return 'text-red-600 bg-red-50 border-red-200'
  }

  const getSearchTypeIcon = (searchType) => {
    switch (searchType) {
      case 'pinecone':
        return { icon: '🧠', label: 'Vector Search', color: 'bg-purple-100 text-purple-800' }
      case 'postgres':
        return { icon: '📊', label: 'Full-text Search', color: 'bg-blue-100 text-blue-800' }
      case 'faiss':
        return { icon: '⚡', label: 'FAISS Search', color: 'bg-green-100 text-green-800' }
      default:
        return { icon: '🔍', label: 'Hybrid Search', color: 'bg-gray-100 text-gray-800' }
    }
  }

  const searchInfo = getSearchTypeIcon(paper.search_type)

  return (
    <div className="fixed inset-0 bg-slate-900 bg-opacity-50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl card-shadow-lg max-w-5xl w-full max-h-[90vh] overflow-hidden">
        {/* Professional Header */}
        <div className="gradient-bg text-white p-6 relative overflow-hidden">
          <div className="absolute inset-0 bg-white bg-opacity-10"></div>
          <div className="relative flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-3 mb-3">
                <div className="w-12 h-12 bg-white bg-opacity-20 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-2xl font-bold mb-1 pr-8 leading-tight">
                    {paper.title}
                  </h2>
                  <div className="flex items-center space-x-4 text-blue-100">
                    <span className="flex items-center space-x-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 4v16l4-2 4 2V4M7 4h10" />
                      </svg>
                      <span className="font-mono text-sm">{paper.paper_id}</span>
                    </span>
                    <span className="bg-white bg-opacity-20 px-3 py-1 rounded-lg text-sm font-semibold">
                      {(paper.score * 100).toFixed(1)}% Match
                    </span>
                    <span className={`px-3 py-1 rounded-lg text-sm font-semibold ${searchInfo.color}`}>
                      {searchInfo.icon} {searchInfo.label}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="relative bg-white bg-opacity-20 hover:bg-opacity-30 p-2 rounded-xl transition-all duration-200"
            >
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Professional Tabs */}
        <div className="border-b border-slate-200 bg-slate-50">
          <nav className="flex space-x-0 px-6">
            {[
              { id: 'overview', label: 'Overview', icon: 'M9 5H7a2 2 0 00-2 2v6a2 2 0 002 2h6a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
              { id: 'abstract', label: 'Abstract', icon: 'M4 6h16M4 10h16M4 14h16M4 18h16' },
              { id: 'details', label: 'Metadata', icon: 'M9 5H7a2 2 0 00-2 2v6a2 2 0 002 2h6a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 py-4 px-4 border-b-2 font-semibold text-sm transition-all duration-200 ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600 bg-white'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={tab.icon} />
                </svg>
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">👥 Authors</h3>
                {paper.authors ? (
                  <p className="text-gray-700 bg-gray-50 p-3 rounded-lg">
                    {paper.authors}
                  </p>
                ) : (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                    <p className="text-yellow-800 text-sm">
                      No author information available.
                    </p>
                  </div>
                )}
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">📊 Search Metrics</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">
                      {(paper.score * 100).toFixed(1)}%
                    </div>
                    <div className="text-sm text-blue-800">Relevance Score</div>
                  </div>
                  <div className="bg-purple-50 p-4 rounded-lg">
                    <div className="text-lg font-bold text-purple-600">
                      {searchInfo.label}
                    </div>
                    <div className="text-sm text-purple-800">Search Method</div>
                  </div>
                </div>
              </div>

              {paper.text && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">🎯 Relevant Content</h3>
                  <p className="text-gray-700 bg-yellow-50 p-3 rounded-lg border-l-4 border-yellow-400">
                    {paper.text}
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'abstract' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">📝 Abstract</h3>
              <div className="prose max-w-none">
                {paper.abstract ? (
                  <MarkdownText 
                    text={paper.abstract} 
                    className="text-gray-700 leading-relaxed"
                  />
                ) : (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <p className="text-yellow-800 text-sm">
                      No abstract available for this paper.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'details' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">🔍 Technical Details</h3>
                <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                  <div className="flex justify-between">
                    <span className="font-medium text-gray-600">Paper ID:</span>
                    <span className="text-gray-900 font-mono">{paper.paper_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium text-gray-600">Search Type:</span>
                    <span className="text-gray-900">{paper.search_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium text-gray-600">Relevance Score:</span>
                    <span className="text-gray-900">{paper.score.toFixed(6)}</span>
                  </div>
                  {paper.chunk_id && (
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600">Chunk ID:</span>
                      <span className="text-gray-900 font-mono">{paper.chunk_id}</span>
                    </div>
                  )}
                  {paper.categories && (
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600">Categories:</span>
                      <span className="text-gray-900">{paper.categories}</span>
                    </div>
                  )}
                  {paper.pdf_path && (
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600">PDF Path:</span>
                      <span className="text-gray-900 font-mono text-sm">{paper.pdf_path}</span>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">📊 Content Statistics</h3>
                <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                  <div className="flex justify-between">
                    <span className="font-medium text-gray-600">Abstract Length:</span>
                    <span className="text-gray-900">{paper.abstract ? paper.abstract.length : 0} characters</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-medium text-gray-600">Abstract Word Count:</span>
                    <span className="text-gray-900">{paper.abstract ? paper.abstract.split(' ').length : 0} words</span>
                  </div>
                  {paper.text_length && (
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600">Full Text Length:</span>
                      <span className="text-gray-900">{paper.text_length.toLocaleString()} characters</span>
                    </div>
                  )}
                  {paper.word_count && (
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600">Full Text Word Count:</span>
                      <span className="text-gray-900">{paper.word_count.toLocaleString()} words</span>
                    </div>
                  )}
                  {paper.text && (
                    <div className="flex justify-between">
                      <span className="font-medium text-gray-600">Relevant Text Length:</span>
                      <span className="text-gray-900">{paper.text.length} characters</span>
                    </div>
                  )}
                </div>
              </div>

              {paper.full_text_preview && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">📄 Full Text Preview</h3>
                  <div className="bg-blue-50 rounded-lg p-4">
                    <MarkdownText 
                      text={paper.full_text_preview} 
                      className="text-gray-700 text-sm leading-relaxed"
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center text-sm text-gray-500">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              This paper was found using {searchInfo.label.toLowerCase()}
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PaperDetail

