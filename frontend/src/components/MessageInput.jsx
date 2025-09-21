import { useState } from 'react'

const MessageInput = ({ onSendMessage, disabled }) => {
  const [message, setMessage] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (message.trim() && !disabled) {
      onSendMessage(message.trim())
      setMessage('')
    }
  }

  return (
    <div className="input-container">
      <form onSubmit={handleSubmit} className="input-form">
        <div className="input-wrapper">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask about research papers..."
            className="message-input"
            disabled={disabled}
          />
          <div className="input-icon">
            <svg className="input-icon-svg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </div>
        </div>
        <button
          type="submit"
          disabled={disabled || !message.trim()}
          className="send-button"
        >
          <div className="send-button-content">
            <span>Send</span>
            <svg className="send-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </div>
        </button>
      </form>
    </div>
  )
}

export default MessageInput
