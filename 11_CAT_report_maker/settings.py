from pydantic import BaseModel, Field
from cat.mad_hatter.decorators import plugin


class MySettings(BaseModel):
    """
    Settings per il plugin Report Maker.
    Permette di configurare il nome del tool e i prompt per ogni tipo di report.
    """
    
    tool_name: str = Field(
        default="Report Maker",
        title="Tool Name",
        description="Nome del tool visualizzato nell'interfaccia"
    )
    create_report_in_word_description: str = Field(
        default="- Use 'create_report_in_word' only for explicit user requests for a document or summary in Word format.",
        title="Create Report In Word Description",
        description="Descrizione prompt del tool create_report_in_word",
        extra={"type": "TextArea"}
    )
    # ========== PROMPT PER TIPI DI REPORT ==========
    
    standard_report_prompt: str = Field(
        default="""You are tasked with creating a comprehensive, professional report in Markdown format.

## Instructions for Report Creation

Based on the conversation history, retrieved documents, and user's request, create a well-structured report that includes:

1. **Title**: A clear, descriptive title for the report
2. **Executive Summary**: A brief overview (2-3 paragraphs)
3. **Main Content**: Organized in logical sections with headers
4. **Key Findings**: Bullet points of important discoveries or conclusions
5. **Data/Tables**: If applicable, include relevant data in table format
6. **Recommendations**: Actionable next steps or suggestions
7. **Conclusion**: Final thoughts and summary

## Formatting Guidelines

Use proper Markdown syntax:
- # for main title (H1)
- ## for major sections (H2)
- ### for subsections (H3)
- **bold** for emphasis
- *italic* for subtle emphasis
- - or * for bullet lists
- 1. 2. 3. for numbered lists
- | tables | with | pipes |
- > for quotes or important notes

## Important Notes

- Be comprehensive but concise
- Use professional language
- Include specific details from the context
- Organize information logically
- Make sure the report is self-contained and understandable""",
        title="Standard Report Prompt",
        description="Prompt template for standard general-purpose reports",
        extra={"type": "TextArea"}
    )
    
    technical_report_prompt: str = Field(
        default="""You are creating a detailed technical report in Markdown format.

## Technical Report Structure

1. **Title & Metadata**: Include title, date, and version
2. **Abstract**: Brief technical overview
3. **Introduction**: Background and objectives
4. **Methodology**: Approach and tools used
5. **Technical Analysis**: Detailed findings with data
6. **Results**: Key outcomes and metrics
7. **Discussion**: Interpretation and implications
8. **Recommendations**: Technical next steps
9. **Conclusion**: Summary and future work
10. **References**: Sources and citations if applicable

## Technical Writing Guidelines

- Use precise technical terminology
- Include code snippets in ```language blocks when relevant
- Present data in tables for clarity
- Use diagrams descriptions when helpful
- Be specific with metrics and measurements
- Follow IEEE or similar technical writing standards""",
        title="Technical Report Prompt",
        description="Prompt template for detailed technical documentation",
        extra={"type": "TextArea"}
    )
    
    business_report_prompt: str = Field(
        default="""You are creating a business-focused executive report in Markdown format.

## Business Report Structure

1. **Executive Summary**: High-level overview for decision makers
2. **Business Context**: Current situation and challenges
3. **Analysis**: Key insights and findings
4. **Strategic Implications**: Business impact assessment
5. **Recommendations**: Actionable business decisions
6. **Implementation Plan**: Next steps with timeline
7. **Risk Assessment**: Potential challenges and mitigation
8. **ROI/Value Proposition**: Expected benefits
9. **Conclusion**: Summary and call to action

## Business Writing Guidelines

- Use clear, non-technical language
- Focus on business value and ROI
- Include metrics and KPIs
- Highlight strategic implications
- Provide actionable recommendations
- Use tables for comparative analysis
- Keep executives' time in mind (concise but complete)""",
        title="Business Report Prompt",
        description="Prompt template for business and executive reports",
        extra={"type": "TextArea"}
    )
    
    executive_summary_report_prompt: str = Field(
        default="""Based on the following context, create a concise executive summary (2-3 paragraphs) that highlights:
- Key topics discussed
- Main findings or conclusions
- Critical insights

Focus on providing a high-level overview that busy executives can quickly understand.""",
        title="Executive Summary Prompt",
        description="Prompt template for concise executive summaries",
        extra={"type": "TextArea"}
    )


@plugin
def settings_model():
    """
    Restituisce il modello Pydantic delle impostazioni.
    Il framework usa questo per validare e salvare i settings.
    """
    return MySettings
