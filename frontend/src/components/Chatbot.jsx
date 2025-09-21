import { useState, useEffect } from 'react'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import PaperList from './PaperList'
import PaperDetail from './PaperDetail'

const Chatbot = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: "Welcome to the ArXiv Research Assistant! I'm an AI-powered research companion that can help you explore and understand astronomy and astrophysics research. I have access to 497 research papers and can provide detailed answers while finding relevant papers for you to explore. Ask me anything about black holes, galaxies, exoplanets, cosmic phenomena, or any other astronomical topics!",
      sender: 'bot',
      timestamp: new Date()
    }
  ])
  const [isLoading, setIsLoading] = useState(false)
  const [backendStatus, setBackendStatus] = useState('checking')
  const [conversationId, setConversationId] = useState(null)
  const [currentPapers, setCurrentPapers] = useState([])
  const [selectedPaper, setSelectedPaper] = useState(null)
  const [showPaperDetail, setShowPaperDetail] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  // Check backend health on component mount
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        // Check both regular health and RAG health
        const [healthResponse, chatHealthResponse] = await Promise.all([
          fetch('http://localhost:8000/api/v1/health'),
          fetch('http://localhost:8000/api/v1/chat/health')
        ])
        
        if (healthResponse.ok && chatHealthResponse.ok) {
          const chatHealth = await chatHealthResponse.json()
          // Check if RAG service is actually healthy
          if (chatHealth.rag_service === 'healthy') {
            setBackendStatus('online')
          } else {
            setBackendStatus('degraded')
          }
        } else {
          setBackendStatus('offline')
        }
      } catch (error) {
        setBackendStatus('offline')
        console.warn('Backend health check failed:', error)
      }
    }

    checkBackendHealth()
  }, [])

  const handleSendMessage = async (message) => {
    const userMessage = {
      id: Date.now(),
      text: message,
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    try {
      const response = await fetch('http://localhost:8000/api/v1/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: message,
          conversation_id: conversationId,
          n_results: 5,
          search_type: "both",
          max_context_messages: 5
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const ragResponse = await response.json()
      
      // Use the generated RAG response (clean, without metadata)
      let responseText = ragResponse.response || "I couldn't generate a response for your query."
      
      // Store conversation ID for future messages
      if (ragResponse.conversation_id && !conversationId) {
        setConversationId(ragResponse.conversation_id)
        console.log('New conversation started:', ragResponse.conversation_id)
      }

      // Update papers section
      if (ragResponse.sources && ragResponse.sources.length > 0) {
        setCurrentPapers(ragResponse.sources)
        console.log('Updated papers:', ragResponse.sources.length)
      }

      // Clean response without metadata - papers shown in separate section
      
      const botMessage = {
        id: Date.now() + 1,
        text: responseText,
        sender: 'bot',
        timestamp: new Date()
      }

      setMessages(prev => [...prev, botMessage])
    } catch (error) {
      console.error('Error:', error)
      
      let errorText = "Sorry, I encountered an error while processing your request."
      
      if (error.message.includes('HTTP error! status: 500')) {
        errorText = "The search service is currently unavailable. Please try again later."
      } else if (error.message.includes('HTTP error! status: 404')) {
        errorText = "The search endpoint was not found. Please check if the backend server is running."
      } else if (error.message.includes('Failed to fetch')) {
        errorText = "Cannot connect to the backend server. Please ensure the server is running on http://localhost:8000"
      }
      
      const errorMessage = {
        id: Date.now() + 1,
        text: errorText,
        sender: 'bot',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleNewConversation = () => {
    setConversationId(null)
    setCurrentPapers([])
    setSelectedPaper(null)
    setShowPaperDetail(false)
    setMessages([{
      id: 1,
      text: "Welcome to the ArXiv Research Assistant! I'm an AI-powered research companion that can help you explore and understand astronomy and astrophysics research. I have access to 497 research papers and can provide detailed answers while finding relevant papers for you to explore. Ask me anything about black holes, galaxies, exoplanets, cosmic phenomena, or any other astronomical topics!",
      sender: 'bot',
      timestamp: new Date()
    }])
    console.log('Started new conversation')
  }

  const handlePaperClick = (paper) => {
    setSelectedPaper(paper)
    setShowPaperDetail(true)
    console.log('Selected paper:', paper.paper_id)
  }

  const handleFollowUpClick = (question) => {
    // Add the follow-up question as a user message and send it
    const newMessage = {
      id: Date.now(),
      text: question,
      sender: 'user',
      timestamp: new Date()
    }
    setMessages(prev => [...prev, newMessage])
    sendMessage(question)
  }

  const handleExport = async (format) => {
    if (!conversationId) {
      alert('No conversation to export. Please start a conversation first.')
      return
    }

    setIsExporting(true)
    try {
      const response = await fetch(`http://localhost:8000/api/v1/chat/export/${format}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          query: messages[0]?.text || 'Research Query'
        })
      })
      
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `research_report_${conversationId}.${format}`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      } else if (response.status === 503) {
        // PDF export not available
        const errorData = await response.json()
        alert(`PDF export is not available: ${errorData.detail}. Please use Markdown export instead.`)
      } else {
        const errorText = await response.text()
        console.error('Export error response:', errorText)
        throw new Error(`Export failed: ${response.status} ${response.statusText}`)
      }
    } catch (error) {
      console.error('Export error:', error)
      alert(`Failed to export as ${format.toUpperCase()}. Please try again.`)
    } finally {
      setIsExporting(false)
    }
  }

  const handleClosePaperDetail = () => {
    setShowPaperDetail(false)
    setSelectedPaper(null)
  }

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      {/* Professional Header */}
      <div className="gradient-bg shadow-lg">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-white bg-opacity-20 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">ArXiv Research Assistant</h1>
                  <p className="text-blue-100 text-sm font-medium">Advanced AI Research Platform</p>
                </div>
              </div>
              {conversationId && (
                <div className="bg-white bg-opacity-20 px-3 py-1 rounded-full">
                  <span className="text-blue-100 text-xs font-medium">
                    Session: {conversationId.slice(0, 8)}
                  </span>
                </div>
              )}
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 bg-white bg-opacity-20 px-3 py-2 rounded-lg">
                <div className={`w-2 h-2 rounded-full ${
                  backendStatus === 'online' ? 'bg-emerald-400' : 
                  backendStatus === 'degraded' ? 'bg-amber-400' :
                  backendStatus === 'offline' ? 'bg-red-400' : 'bg-yellow-400'
                }`}></div>
                <span className="text-white text-sm font-medium">
                  {backendStatus === 'online' ? 'System Online' : 
                   backendStatus === 'degraded' ? 'Limited Mode' :
                   backendStatus === 'offline' ? 'System Offline' : 
                   'Connecting...'}
                </span>
              </div>
              
              <button
                onClick={handleNewConversation}
                className="bg-white bg-opacity-20 hover:bg-opacity-30 text-white px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center space-x-2"
                title="Start new conversation"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span>New Chat</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - Professional Split Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Papers Section - Professional Design */}
        <div className="w-1/3 bg-white border-r border-slate-200 flex flex-col shadow-sm">
          <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-slate-900">Research Papers</h3>
                <p className="text-sm text-slate-600">
                  {currentPapers.length > 0 
                    ? `${currentPapers.length} relevant papers found`
                    : 'Ask a question to find papers'
                  }
                </p>
              </div>
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
            </div>
          </div>
          
          <PaperList 
            papers={currentPapers} 
            onPaperClick={handlePaperClick}
            isLoading={isLoading}
          />
        </div>

        {/* Chat Section - Professional Design */}
        <div className="flex-1 flex flex-col bg-white">
          <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-slate-900">AI Research Assistant</h3>
                <p className="text-sm text-slate-600">Ask questions about astronomy and astrophysics research</p>
              </div>
              <div className="flex items-center space-x-3">
                {/* Export Buttons */}
                {conversationId && (
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleExport('markdown')}
                      disabled={isExporting}
                      className="flex items-center space-x-1 px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-300 rounded-md hover:bg-slate-50 hover:text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span>MD</span>
                    </button>
                    <button
                      onClick={() => handleExport('pdf')}
                      disabled={isExporting}
                      className="flex items-center space-x-1 px-3 py-1.5 text-xs font-medium text-red-600 bg-white border border-red-300 rounded-md hover:bg-red-50 hover:text-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                      <span>PDF</span>
                    </button>
                  </div>
                )}
                
                <div className="flex items-center space-x-2 text-sm text-slate-500">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  <span>Powered by GPT-4o</span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex-1 flex flex-col">
            <MessageList messages={messages} isLoading={isLoading} onFollowUpClick={handleFollowUpClick} />
            <MessageInput onSendMessage={handleSendMessage} disabled={isLoading} />
          </div>
        </div>
      </div>

      {/* Paper Detail Modal */}
      <PaperDetail
        paper={selectedPaper}
        isOpen={showPaperDetail}
        onClose={handleClosePaperDetail}
      />
    </div>
  )
}

export default Chatbot
