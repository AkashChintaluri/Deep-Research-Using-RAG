import { useState } from 'react'

const PaperList = ({ papers, onPaperClick, isLoading }) => {
  const [selectedPaper, setSelectedPaper] = useState(null)

  const handlePaperClick = (paper) => {
    setSelectedPaper(paper)
    if (onPaperClick) {
      onPaperClick(paper)
    }
  }

  const getScoreColor = (score) => {
    if (score >= 0.8) return 'text-emerald-700 bg-emerald-50 border-emerald-200'
    if (score >= 0.6) return 'text-amber-700 bg-amber-50 border-amber-200'
    return 'text-slate-600 bg-slate-50 border-slate-200'
  }

  const getSearchTypeIcon = (searchType) => {
    switch (searchType) {
      case 'pinecone':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold bg-violet-100 text-violet-800 border border-violet-200">
            <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Vector
          </span>
        )
      case 'postgres':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
            <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
            </svg>
            Full-text
          </span>
        )
      case 'faiss':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold bg-green-100 text-green-800 border border-green-200">
            <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            FAISS
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200">
            <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Hybrid
          </span>
        )
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-slate-500">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-4"></div>
        <p className="text-base font-medium">Searching research papers...</p>
        <p className="text-sm text-slate-400 mt-1">Analyzing 497 astronomy papers</p>
      </div>
    )
  }

  if (!papers || papers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-slate-500 px-6">
        <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p className="text-lg font-semibold text-slate-700 mb-2">Ready to explore</p>
        <p className="text-sm text-slate-500 text-center leading-relaxed">
          Ask questions about astronomy and astrophysics to discover relevant research papers
        </p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="p-4 space-y-3">
        {papers.map((paper, index) => (
          <div
            key={paper.paper_id || index}
            className={`card-shadow rounded-xl p-5 cursor-pointer transition-all duration-200 hover:card-shadow-hover transform hover:-translate-y-0.5 ${
              selectedPaper?.paper_id === paper.paper_id
                ? 'border-2 border-blue-500 bg-blue-50'
                : 'border border-slate-200 bg-white hover:border-slate-300'
            }`}
            onClick={() => handlePaperClick(paper)}
          >
            {/* Header with ranking and score */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">
                  {index + 1}
                </div>
                {getSearchTypeIcon(paper.search_type)}
              </div>
              <div className={`px-3 py-1.5 rounded-xl text-sm font-semibold border ${getScoreColor(paper.score)}`}>
                {(paper.score * 100).toFixed(1)}%
              </div>
            </div>
            
            {/* Paper title */}
            <h4 className="font-bold text-slate-900 mb-3 line-clamp-2 text-lg leading-tight">
              {paper.title}
            </h4>
            
            {/* Authors */}
            <div className="flex items-center mb-3">
              <svg className="w-4 h-4 text-slate-400 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <p className="text-sm text-slate-600 line-clamp-1 font-medium">
                {paper.authors}
              </p>
            </div>
            
            {/* Abstract preview */}
            <p className="text-sm text-slate-700 line-clamp-3 leading-relaxed mb-4">
              {paper.abstract}
            </p>
            
            {/* Metadata and action */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-100">
              <div className="flex items-center space-x-3 text-xs text-slate-500">
                <span className="font-mono bg-slate-100 px-2 py-1 rounded">
                  {paper.paper_id}
                </span>
                {paper.categories && (
                  <span className="bg-emerald-100 text-emerald-700 px-2 py-1 rounded font-medium">
                    {paper.categories}
                  </span>
                )}
              </div>
              <div className="flex items-center text-sm text-blue-600 hover:text-blue-700 font-medium">
                <span>View details</span>
                <svg className="w-4 h-4 ml-1 transition-transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default PaperList
