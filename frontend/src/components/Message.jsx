import MarkdownText from './MarkdownText'

const Message = ({ message, onFollowUpClick }) => {
  const isUser = message.sender === 'user'
  
  return (
    <div className={`message-container ${isUser ? 'message-container-user' : 'message-container-bot'}`}>
      <div className={`message-bubble ${isUser ? 'message-bubble-user' : 'message-bubble-bot'}`}>
        <div className="message-content">
          {!isUser && (
            <div className="bot-avatar">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
          )}
          
                  <div className="message-text">
                    <MarkdownText text={message.text} className="message-paragraph" />
            
                    {message.sources && message.sources.length > 0 && (
                      <div className="sources-section">
                        <p className="sources-title">Sources:</p>
                        <div className="sources-list">
                          {message.sources.map((source, index) => (
                            <div key={index} className="source-item">
                              <div className="source-content">
                                <span className="source-title">
                                  {source.title || `Source ${index + 1}`}
                                </span>
                                {source.score && (
                                  <span className="source-score">
                                    {(source.score * 100).toFixed(1)}%
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {message.follow_up_questions && message.follow_up_questions.length > 0 && (
                      <div className="follow-up-section">
                        <p className="follow-up-title">💡 Suggested Follow-up Questions:</p>
                        <div className="follow-up-list">
                          {message.follow_up_questions.map((question, index) => (
                            <button
                              key={index}
                              className="follow-up-question"
                              onClick={() => onFollowUpClick && onFollowUpClick(question)}
                            >
                              {question}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {message.reasoning_steps && message.reasoning_steps.length > 0 && (
                      <div className="reasoning-section">
                        <p className="reasoning-title">🧠 Reasoning Process:</p>
                        <div className="reasoning-list">
                          {message.reasoning_steps.map((step, index) => (
                            <div key={index} className="reasoning-step">
                              <span className="step-number">{index + 1}.</span>
                              <span className="step-content">{step}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
            
            <p className="message-timestamp">
              {message.timestamp.toLocaleTimeString()}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Message
