import { useEffect, useRef } from 'react'

const FormattedText = ({ text, className = "" }) => {
  const textRef = useRef(null)

  useEffect(() => {
    if (textRef.current && window.MathJax) {
      // Clear any existing MathJax content
      textRef.current.innerHTML = textRef.current.textContent
      
      // Process MathJax
      window.MathJax.typesetPromise([textRef.current]).catch((err) => {
        console.error('MathJax rendering error:', err)
      })
    }
  }, [text])

  // Function to format text with proper line breaks and formatting
  const formatText = (text) => {
    if (!text) return ''
    
    // First, try to split by double line breaks for paragraphs
    let paragraphs = text.split(/\n\s*\n/).filter(p => p.trim())
    
    // If no double line breaks found, try to split by single line breaks with patterns
    if (paragraphs.length === 1) {
      // Look for patterns that indicate new paragraphs
      const singleLineBreaks = text.split(/\n/).filter(p => p.trim())
      
      // Group lines that belong together
      const groupedParagraphs = []
      let currentParagraph = ''
      
      for (let i = 0; i < singleLineBreaks.length; i++) {
        const line = singleLineBreaks[i].trim()
        
        // Check if this line starts a new paragraph (numbered list, bullet, heading, etc.)
        if (line.match(/^\d+\.\s/) || // Numbered list
            line.match(/^[-•]\s/) || // Bullet list
            line.match(/^#{1,4}\s/) || // Headings
            line.match(/^[A-Z][^:]*:$/) || // Lines ending with colon (like "Key Concept:")
            line.match(/^[A-Z][a-z\s]+:$/) || // Lines ending with colon (like "Wormholes in the Accelerating Universe")
            line.match(/^[A-Z][a-z\s]+---/) || // Lines with dashes (like "---Non-Minimal Wu-Yang Wormholes")
            (i > 0 && line.length > 50 && !line.startsWith(' ') && !line.startsWith('\t'))) { // Long lines that might be new paragraphs
          
          if (currentParagraph.trim()) {
            groupedParagraphs.push(currentParagraph.trim())
          }
          currentParagraph = line
        } else {
          currentParagraph += (currentParagraph ? ' ' : '') + line
        }
      }
      
      if (currentParagraph.trim()) {
        groupedParagraphs.push(currentParagraph.trim())
      }
      
      paragraphs = groupedParagraphs
    }
    
    // Special handling for the specific format we're getting (sections without line breaks)
    if (paragraphs.length === 1) {
      const text = paragraphs[0]
      
      // Split by section headers (## Key Findings, ## Evidence, etc.)
      const sections = text.split(/(?=##\s+[A-Z][^#]+)/)
      
      if (sections.length > 1) {
        paragraphs = sections.filter(s => s.trim())
      } else {
        // Try to split by common patterns in the response
        const patterns = [
          /(?=Key Findings\s*\d+\.)/,
          /(?=Evidence & Analysis)/,
          /(?=Conclusions)/,
          /(?=Follow-up Questions\s*\d+\.)/
        ]
        
        let splitText = text
        for (const pattern of patterns) {
          splitText = splitText.replace(pattern, '\n\n---SECTION---\n\n')
        }
        
        if (splitText.includes('---SECTION---')) {
          paragraphs = splitText.split('---SECTION---').filter(p => p.trim())
        } else {
          // If still no sections found, try to split by the specific patterns we see
          const sectionPatterns = [
            /Key Findings\s*\d+\./,
            /Evidence & Analysis/,
            /Conclusions/,
            /Follow-up Questions\s*\d+\./
          ]
          
          let currentText = text
          let foundSections = false
          
          for (const pattern of sectionPatterns) {
            if (pattern.test(currentText)) {
              currentText = currentText.replace(pattern, (match) => `\n\n---SECTION---\n\n${match}`)
              foundSections = true
            }
          }
          
          if (foundSections) {
            paragraphs = currentText.split('---SECTION---').filter(p => p.trim())
          }
        }
      }
    }
    
    return paragraphs.map((paragraph, index) => {
      const trimmedParagraph = paragraph.trim()
      
      // Handle different types of content
      if (trimmedParagraph.startsWith('#### ')) {
        // Sub-subheading
        return (
          <h4 key={index} className="text-base font-semibold text-gray-900 mb-2 mt-3">
            {processInlineFormatting(trimmedParagraph.replace(/#### /, ''))}
          </h4>
        )
      } else if (trimmedParagraph.startsWith('### ')) {
        // Subheading
        return (
          <h3 key={index} className="text-lg font-semibold text-gray-900 mb-2 mt-4">
            {processInlineFormatting(trimmedParagraph.replace(/### /, ''))}
          </h3>
        )
      } else if (trimmedParagraph.startsWith('## ')) {
        // Heading
        return (
          <h2 key={index} className="text-xl font-bold text-gray-900 mb-3 mt-4">
            {processInlineFormatting(trimmedParagraph.replace(/## /, ''))}
          </h2>
        )
      } else if (trimmedParagraph.startsWith('# ')) {
        // Main heading
        return (
          <h1 key={index} className="text-2xl font-bold text-gray-900 mb-4 mt-4">
            {processInlineFormatting(trimmedParagraph.replace(/# /, ''))}
          </h1>
        )
      } else if (trimmedParagraph.match(/^Key Findings/) || 
                 trimmedParagraph.match(/^Evidence & Analysis/) || 
                 trimmedParagraph.match(/^Conclusions/) || 
                 trimmedParagraph.match(/^Follow-up Questions/)) {
        // Section headers from our specific format
        return (
          <h2 key={index} className="text-xl font-bold text-blue-600 mb-3 mt-4 border-b-2 border-blue-200 pb-2">
            {processInlineFormatting(trimmedParagraph)}
          </h2>
        )
      } else if (trimmedParagraph.match(/^\d+\.\s+[A-Z]/)) {
        // Handle numbered list items that start with capital letters (like "1. Wormholes can exist...")
        const match = trimmedParagraph.match(/^(\d+)\.\s+(.*)/)
        if (match) {
          return (
            <div key={index} className="flex items-start mb-3 ml-4">
              <span className="text-blue-600 mr-2 mt-1 font-semibold min-w-[2rem]">{match[1]}.</span>
              <span className="text-gray-700 flex-1">{processInlineFormatting(match[2])}</span>
            </div>
          )
        }
      } else if (trimmedParagraph.match(/^[A-Z][a-z\s]+:$/) || trimmedParagraph.match(/^[A-Z][a-z\s]+---/)) {
        // Special headings like "Wormholes in the Accelerating Universe:" or "---Non-Minimal Wu-Yang Wormholes"
        const cleanHeading = trimmedParagraph.replace(/^---/, '').replace(/:$/, '')
        return (
          <h3 key={index} className="text-lg font-semibold text-blue-600 mb-3 mt-4 border-l-4 border-blue-500 pl-3">
            {processInlineFormatting(cleanHeading)}
          </h3>
        )
      } else if (trimmedParagraph.match(/^\d+\.\s/)) {
        // Numbered list item - handle multiple items in one paragraph
        const items = trimmedParagraph.split(/(?=\d+\.\s)/).filter(item => item.trim())
        
        if (items.length > 1) {
          // Multiple numbered items in one paragraph
          return (
            <div key={index} className="mb-3">
              {items.map((item, itemIndex) => {
                const match = item.trim().match(/^(\d+)\.\s*(.*)/)
                if (match) {
                  return (
                    <div key={itemIndex} className="flex items-start mb-2 ml-4">
                      <span className="text-blue-600 mr-2 mt-1 font-semibold min-w-[2rem]">{match[1]}.</span>
                      <span className="text-gray-700 flex-1">{processInlineFormatting(match[2])}</span>
                    </div>
                  )
                }
                return null
              })}
            </div>
          )
        } else {
          // Single numbered item
          const match = trimmedParagraph.match(/^(\d+)\.\s*(.*)/)
          if (match) {
            return (
              <div key={index} className="flex items-start mb-2 ml-4">
                <span className="text-blue-600 mr-2 mt-1 font-semibold min-w-[2rem]">{match[1]}.</span>
                <span className="text-gray-700 flex-1">{processInlineFormatting(match[2])}</span>
              </div>
            )
          }
        }
      } else if (trimmedParagraph.startsWith('- ') || trimmedParagraph.startsWith('• ')) {
        // List item
        return (
          <div key={index} className="flex items-start mb-2 ml-4">
            <span className="text-blue-600 mr-2 mt-1 min-w-[1rem]">•</span>
            <span className="text-gray-700 flex-1">{processInlineFormatting(trimmedParagraph.replace(/^[-•] /, ''))}</span>
          </div>
        )
      } else if (trimmedParagraph.match(/^-\s+[A-Z]/)) {
        // Handle bullet points that start with capital letters (like "- The 'big trip' process...")
        const content = trimmedParagraph.replace(/^-\s+/, '')
        return (
          <div key={index} className="flex items-start mb-2 ml-4">
            <span className="text-blue-600 mr-2 mt-1 min-w-[1rem]">•</span>
            <span className="text-gray-700 flex-1">{processInlineFormatting(content)}</span>
          </div>
        )
      } else {
        // Regular paragraph - process for inline formatting including bold, italic, math, etc.
        // Also handle single line breaks within paragraphs
        const processedText = processInlineFormatting(trimmedParagraph.replace(/\n/g, '<br/>'))
        return (
          <p key={index} className="text-gray-700 mb-3 leading-relaxed">
            {processedText}
          </p>
        )
      }
    })
  }

  // Function to process inline formatting like units, symbols, etc.
  const processInlineFormatting = (text) => {
    if (!text) return text
    
    // Process bold text (**text**) - use non-greedy matching
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-bold text-gray-900">$1</strong>')
    
    // Process italic text (*text*) - simple approach
    text = text.replace(/\*([^*\n]+)\*/g, '<em class="italic text-gray-800">$1</em>')
    
    // Process units (e.g., "10 km/s", "5.2 × 10^6 M☉")
    text = text.replace(/(\d+(?:\.\d+)?)\s*(km\/s|m\/s|pc|kpc|Mpc|Gpc|M☉|L☉|K|°C|°F|eV|keV|MeV|GeV|TeV|Hz|kHz|MHz|GHz|THz|nm|μm|mm|cm|m|km|g|kg|s|min|h|d|yr|Myr|Gyr)/g, 
      '<span class="unit">$1 $2</span>')
    
    // Process physical constants (e.g., "c", "G", "h", "k_B")
    text = text.replace(/\b(c|G|h|k_B|e|m_e|m_p|R_\d+|N_A|σ|ε_0|μ_0)\b/g, 
      '<span class="constant">$1</span>')
    
    // Process chemical formulas (e.g., "H₂O", "CO₂", "CH₄")
    text = text.replace(/([A-Z][a-z]?)(\d+)/g, 
      '<span class="chemical">$1<sub>$2</sub></span>')
    
    // Process superscripts (e.g., "x²", "E=mc²")
    text = text.replace(/([a-zA-Z0-9])\^(\d+)/g, 
      '$1<sup>$2</sup>')
    
    // Process subscripts (e.g., "H₂", "CO₂")
    text = text.replace(/([a-zA-Z])_(\d+)/g, 
      '$1<sub>$2</sub>')
    
    // Process Greek letters
    text = text.replace(/\b(alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|sigma|tau|phi|omega)\b/g, 
      (match) => {
        const greekMap = {
          'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'epsilon': 'ε',
          'theta': 'θ', 'lambda': 'λ', 'mu': 'μ', 'pi': 'π', 'sigma': 'σ',
          'tau': 'τ', 'phi': 'φ', 'omega': 'ω'
        }
        return greekMap[match] || match
      })
    
    return <span dangerouslySetInnerHTML={{ __html: text }} />
  }

  return (
    <div ref={textRef} className={`formatted-text ${className}`}>
      {formatText(text)}
    </div>
  )
}

export default FormattedText
