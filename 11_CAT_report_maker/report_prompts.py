"""
Modulo per la gestione dei prompt di generazione report.

Questo modulo contiene tutte le funzioni e template per generare
prompt che l'LLM utilizzerà per creare il contenuto dei report.

I template vengono sempre caricati dai settings del plugin.
"""


def generate_report_prompt(full_context: str, user_request: str, prompt_template: str) -> str:
    """
    Genera il prompt completo per la creazione del report.
    
    Args:
        full_context: Contesto completo della conversazione (history, memories, tools)
        user_request: Richiesta specifica dell'utente
        prompt_template: Template del prompt dai settings
    
    Returns:
        str: Prompt formattato per l'LLM
    """
    
    prompt = f"""{prompt_template}

{full_context}

**User's Specific Request**: {user_request}

Now generate the complete report in Markdown format:"""
    
    return prompt


def generate_executive_summary_prompt(context: str, prompt_template: str) -> str:
    """
    Genera un prompt specifico per l'executive summary.
    
    Args:
        context: Contesto della conversazione
        prompt_template: Template del prompt dai settings
    
    Returns:
        str: Prompt per generare l'executive summary
    """
    
    prompt = f"""{prompt_template}

Context:
{context}

Executive Summary:"""
    
    return prompt


def generate_technical_report_prompt(full_context: str, user_request: str, prompt_template: str) -> str:
    """
    Genera un prompt per report tecnici più dettagliati.
    
    Args:
        full_context: Contesto completo
        user_request: Richiesta dell'utente
        prompt_template: Template del prompt dai settings
    
    Returns:
        str: Prompt per report tecnico
    """
    
    prompt = f"""{prompt_template}

{full_context}

**User's Technical Request**: {user_request}

Generate the technical report:"""
    
    return prompt


def generate_business_report_prompt(full_context: str, user_request: str, prompt_template: str) -> str:
    """
    Genera un prompt per report business/executive.
    
    Args:
        full_context: Contesto completo
        user_request: Richiesta dell'utente
        prompt_template: Template del prompt dai settings
    
    Returns:
        str: Prompt per report business
    """
    
    prompt = f"""{prompt_template}

{full_context}

**User's Business Request**: {user_request}

Generate the business report:"""
    
    return prompt


# Dizionario per facilitare la selezione del tipo di prompt
PROMPT_FUNCTIONS = {
    'standard': generate_report_prompt,
    'technical': generate_technical_report_prompt,
    'business': generate_business_report_prompt,
    'executive_summary': generate_executive_summary_prompt,
}


def get_prompt_by_type(
    prompt_type: str, 
    full_context: str, 
    user_request: str = "",
    settings: dict = None
) -> str:
    """
    Ottiene il prompt appropriato in base al tipo richiesto.
    
    Args:
        prompt_type: Tipo di prompt ('standard', 'technical', 'business', 'executive_summary')
        full_context: Contesto completo
        user_request: Richiesta dell'utente (opzionale per executive_summary)
        settings: Settings del plugin con template personalizzati (obbligatorio)
    
    Returns:
        str: Prompt generato
    
    Raises:
        ValueError: Se il tipo di prompt non è supportato
        KeyError: Se il template non è trovato nei settings
    """
    
    if prompt_type not in PROMPT_FUNCTIONS:
        raise ValueError(
            f"Prompt type '{prompt_type}' not supported. "
            f"Available types: {list(PROMPT_FUNCTIONS.keys())}"
        )
    
    # Recupera il template dai settings (obbligatorio)
    template_key = f"{prompt_type}_report_prompt"
    
    if not settings or template_key not in settings:
        raise KeyError(
            f"Template '{template_key}' not found in settings. "
            f"Please configure it in the plugin settings."
        )
    
    prompt_template = settings[template_key]
    prompt_function = PROMPT_FUNCTIONS[prompt_type]
    
    # executive_summary ha una signature diversa
    if prompt_type == 'executive_summary':
        return prompt_function(full_context, prompt_template=prompt_template)
    
    return prompt_function(full_context, user_request, prompt_template=prompt_template)