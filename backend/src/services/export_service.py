"""
Export service for generating research reports in various formats.
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import markdown

# WeasyPrint availability will be checked at runtime
WEASYPRINT_AVAILABLE = False

# Alternative PDF generation using reportlab
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from ..models.search import SearchResult

logger = logging.getLogger(__name__)

class ExportService:
    """Service for exporting research reports in different formats."""
    
    def __init__(self):
        self.export_dir = Path("exports")
        self.export_dir.mkdir(exist_ok=True)
        
    def export_to_markdown(self, 
                          response: str, 
                          sources: List[Dict[str, Any]], 
                          query: str,
                          conversation_id: Optional[str] = None,
                          follow_up_questions: Optional[List[str]] = None,
                          reasoning_steps: Optional[List[str]] = None,
                          research_summary: Optional[Dict[str, Any]] = None,
                          conversation_history: Optional[List[Dict[str, Any]]] = None) -> str:
        """Export research report to Markdown format."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"research_report_{timestamp}.md"
            filepath = self.export_dir / filename
            
            # Create markdown content
            markdown_content = self._generate_markdown_content(
                response, sources, query, conversation_id, 
                follow_up_questions, reasoning_steps, research_summary, conversation_history
            )
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Markdown export created: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Markdown export failed: {e}")
            raise
    
    def export_to_pdf(self, 
                     response: str, 
                     sources: List[Dict[str, Any]], 
                     query: str,
                     conversation_id: Optional[str] = None,
                     follow_up_questions: Optional[List[str]] = None,
                     reasoning_steps: Optional[List[str]] = None,
                     research_summary: Optional[Dict[str, Any]] = None,
                     conversation_history: Optional[List[Dict[str, Any]]] = None) -> str:
        """Export research report to PDF format."""
        # Check WeasyPrint availability at runtime
        weasyprint_available = self._check_weasyprint_availability()
        
        if not weasyprint_available and not REPORTLAB_AVAILABLE:
            raise ImportError("No PDF generation libraries available. Please install WeasyPrint or ReportLab, or use Markdown export instead.")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"research_report_{timestamp}.pdf"
            filepath = self.export_dir / filename
            
            if weasyprint_available:
                # Use WeasyPrint for better HTML/CSS support
                return self._export_pdf_weasyprint(
                    response, sources, query, conversation_id,
                    follow_up_questions, reasoning_steps, research_summary, filepath
                )
            elif REPORTLAB_AVAILABLE:
                # Use ReportLab as fallback
                return self._export_pdf_reportlab(
                    response, sources, query, conversation_id,
                    follow_up_questions, reasoning_steps, research_summary, filepath
                )
            
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            raise
    
    def _check_weasyprint_availability(self) -> bool:
        """Check if WeasyPrint is available at runtime."""
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            return True
        except (ImportError, OSError):
            return False
    
    def _export_pdf_weasyprint(self, response, sources, query, conversation_id, 
                              follow_up_questions, reasoning_steps, research_summary, conversation_history, filepath):
        """Export PDF using WeasyPrint."""
        # Import WeasyPrint modules locally
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        
        # Generate HTML content
        html_content = self._generate_html_content(
            response, sources, query, conversation_id,
            follow_up_questions, reasoning_steps, research_summary, conversation_history
        )
        
        # Convert to PDF using WeasyPrint
        font_config = FontConfiguration()
        html_doc = HTML(string=html_content)
        css = CSS(string=self._get_pdf_css())
        
        html_doc.write_pdf(
            filepath, 
            stylesheets=[css], 
            font_config=font_config
        )
        
        logger.info(f"PDF export created with WeasyPrint: {filepath}")
        return str(filepath)
    
    def _export_pdf_reportlab(self, response, sources, query, conversation_id,
                             follow_up_questions, reasoning_steps, research_summary, filepath):
        """Export PDF using ReportLab."""
        doc = SimpleDocTemplate(str(filepath), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph("Research Report", title_style))
        story.append(Spacer(1, 12))
        
        # Metadata
        meta_style = ParagraphStyle(
            'Meta',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey
        )
        story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", meta_style))
        story.append(Paragraph(f"<b>Query:</b> {query}", meta_style))
        story.append(Paragraph(f"<b>Conversation ID:</b> {conversation_id or 'N/A'}", meta_style))
        story.append(Spacer(1, 20))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        # Clean response text for ReportLab
        clean_response = self._clean_text_for_reportlab(response)
        story.append(Paragraph(clean_response, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Sources
        if sources:
            story.append(Paragraph("Sources Analyzed", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            for i, source in enumerate(sources, 1):
                story.append(Paragraph(f"<b>Source {i}: {source.get('title', 'Unknown Title')}</b>", styles['Heading3']))
                story.append(Paragraph(f"<b>Authors:</b> {source.get('authors', 'Unknown Authors')}", styles['Normal']))
                story.append(Paragraph(f"<b>Relevance Score:</b> {source.get('score', 0):.3f}", styles['Normal']))
                story.append(Paragraph(f"<b>Search Type:</b> {source.get('search_type', 'Unknown')}", styles['Normal']))
                
                if source.get('abstract'):
                    abstract = self._clean_text_for_reportlab(source['abstract'])
                    story.append(Paragraph(f"<b>Abstract:</b> {abstract[:500]}{'...' if len(abstract) > 500 else ''}", styles['Normal']))
                
                story.append(Spacer(1, 12))
        
        # Follow-up questions
        if follow_up_questions:
            story.append(Paragraph("Suggested Follow-up Questions", styles['Heading2']))
            story.append(Spacer(1, 12))
            for i, question in enumerate(follow_up_questions, 1):
                story.append(Paragraph(f"{i}. {question}", styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"PDF export created with ReportLab: {filepath}")
        return str(filepath)
    
    def _clean_text_for_reportlab(self, text):
        """Clean text for ReportLab PDF generation."""
        if not text:
            return ""
        
        # Remove markdown formatting that ReportLab doesn't handle well
        import re
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)      # Italic
        text = re.sub(r'#{1,6}\s*', '', text)                # Headers
        text = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', text)  # Code
        
        # Escape HTML characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        return text
    
    def _generate_markdown_content(self, 
                                  response: str, 
                                  sources: List[Dict[str, Any]], 
                                  query: str,
                                  conversation_id: Optional[str] = None,
                                  follow_up_questions: Optional[List[str]] = None,
                                  reasoning_steps: Optional[List[str]] = None,
                                  research_summary: Optional[Dict[str, Any]] = None,
                                  conversation_history: Optional[List[Dict[str, Any]]] = None) -> str:
        """Generate markdown content for the research report."""
        
        content = f"""# Research Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Query:** {query}  
**Conversation ID:** {conversation_id or 'N/A'}

---

## Executive Summary

{response}

---

## Conversation History

"""
        
        # Add conversation history if available
        if conversation_history:
            content += "The following conversation led to this research report:\n\n"
            for i, message in enumerate(conversation_history, 1):
                message_type = message.get('message_type', 'unknown')
                message_content = message.get('content', '')
                timestamp = message.get('timestamp', '')
                
                if message_type == 'user':
                    content += f"**User {i}:** {message_content}\n\n"
                elif message_type == 'assistant':
                    content += f"**Assistant {i}:** {message_content}\n\n"
                
                if timestamp:
                    content += f"*Timestamp: {timestamp}*\n\n"
        else:
            content += "No conversation history available.\n\n"
        
        content += """---

## Research Analysis

### Sources Analyzed
Total papers analyzed: {len(sources)}

"""
        
        # Add sources
        for i, source in enumerate(sources, 1):
            content += f"""### Source {i}: {source.get('title', 'Unknown Title')}

**Authors:** {source.get('authors', 'Unknown Authors')}  
**Relevance Score:** {source.get('score', 0):.3f}  
**Search Type:** {source.get('search_type', 'Unknown')}

**Abstract:**
{source.get('abstract', 'No abstract available')}

**Categories:** {source.get('categories', 'N/A')}

---

"""
        
        # Add reasoning steps if available
        if reasoning_steps:
            content += """## Methodology & Reasoning

"""
            for i, step in enumerate(reasoning_steps, 1):
                content += f"{i}. {step}\n"
            content += "\n---\n\n"
        
        # Add research summary if available
        if research_summary:
            content += f"""## Research Summary

**Total Papers:** {research_summary.get('total_papers', 0)}  
**Date Range:** {research_summary.get('date_range', {}).get('earliest', 'N/A')} - {research_summary.get('date_range', {}).get('latest', 'N/A')}

### Key Findings
"""
            for finding in research_summary.get('key_findings', []):
                content += f"- {finding}\n"
            
            if research_summary.get('research_gaps'):
                content += "\n### Research Gaps\n"
                for gap in research_summary.get('research_gaps', []):
                    content += f"- {gap}\n"
            
            content += "\n---\n\n"
        
        # Add follow-up questions if available
        if follow_up_questions:
            content += """## Suggested Follow-up Questions

"""
            for i, question in enumerate(follow_up_questions, 1):
                content += f"{i}. {question}\n"
            content += "\n---\n\n"
        
        content += f"""## Export Information

- **Export Format:** Markdown
- **Generated by:** ArXiv Research Assistant
- **Export Time:** {datetime.now().isoformat()}
- **Query:** {query}
"""
        
        return content
    
    def _generate_html_content(self, 
                              response: str, 
                              sources: List[Dict[str, Any]], 
                              query: str,
                              conversation_id: Optional[str] = None,
                              follow_up_questions: Optional[List[str]] = None,
                              reasoning_steps: Optional[List[str]] = None,
                              research_summary: Optional[Dict[str, Any]] = None) -> str:
        """Generate HTML content for PDF export."""
        
        # Convert markdown to HTML
        markdown_content = self._generate_markdown_content(
            response, sources, query, conversation_id,
            follow_up_questions, reasoning_steps, research_summary
        )
        
        html_content = markdown.markdown(
            markdown_content, 
            extensions=['tables', 'fenced_code', 'toc']
        )
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Research Report - {query}</title>
    <style>
        {self._get_pdf_css()}
    </style>
</head>
<body>
    {html_content}
</body>
</html>"""
    
    def _get_pdf_css(self) -> str:
        """Get CSS styles for PDF export."""
        return """
        body {
            font-family: 'Times New Roman', serif;
            line-height: 1.6;
            margin: 2cm;
            color: #333;
        }
        
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }
        
        h2 {
            color: #34495e;
            border-bottom: 2px solid #bdc3c7;
            padding-bottom: 5px;
            margin-top: 30px;
            margin-bottom: 20px;
        }
        
        h3 {
            color: #2c3e50;
            margin-top: 25px;
            margin-bottom: 15px;
        }
        
        h4 {
            color: #7f8c8d;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        p {
            margin-bottom: 15px;
            text-align: justify;
        }
        
        ul, ol {
            margin-bottom: 15px;
            padding-left: 30px;
        }
        
        li {
            margin-bottom: 5px;
        }
        
        blockquote {
            border-left: 4px solid #3498db;
            margin: 20px 0;
            padding: 10px 20px;
            background-color: #f8f9fa;
        }
        
        code {
            background-color: #f1f2f6;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        
        pre {
            background-color: #f1f2f6;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        
        .page-break {
            page-break-before: always;
        }
        
        .source-item {
            margin-bottom: 20px;
            padding: 15px;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            background-color: #fafafa;
        }
        
        .score {
            color: #27ae60;
            font-weight: bold;
        }
        
        .authors {
            color: #7f8c8d;
            font-style: italic;
        }
        
        @media print {
            body { margin: 1cm; }
            .page-break { page-break-before: always; }
        }
        """
    
    def list_exports(self) -> List[Dict[str, Any]]:
        """List all available export files."""
        try:
            exports = []
            for file_path in self.export_dir.glob("*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    exports.append({
                        "filename": file_path.name,
                        "filepath": str(file_path),
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "format": file_path.suffix[1:].upper()
                    })
            
            return sorted(exports, key=lambda x: x["created"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list exports: {e}")
            return []
    
    def delete_export(self, filename: str) -> bool:
        """Delete an export file."""
        try:
            file_path = self.export_dir / filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted export: {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete export {filename}: {e}")
            return False
