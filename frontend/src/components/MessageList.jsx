import Message from './Message'

const MessageList = ({ messages, isLoading, onFollowUpClick }) => {
  return (
    <div className="message-list">
      {messages.map((message, index) => (
        <div 
          key={message.id} 
          className="message-item"
        >
          <Message message={message} onFollowUpClick={onFollowUpClick} />
        </div>
      ))}
      
      {isLoading && (
        <div className="loading-container">
          <div className="loading-bubble">
            <div className="loading-content">
              <div className="loading-dots">
                <div className="loading-dot"></div>
                <div className="loading-dot animation-delay-100"></div>
                <div className="loading-dot animation-delay-200"></div>
              </div>
              <span className="loading-text">Thinking...</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MessageList
