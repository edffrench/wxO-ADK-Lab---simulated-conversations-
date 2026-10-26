"""
Signature stubs of the agent's real web-search tools, used only so that
`orchestrate evaluations generate` knows which tools exist. They are not imported
into wxO; the deployed tools are gemini_flash_search_6545c / gemini_pro_search_39a85.
"""
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


@tool(name="gemini_flash_search_6545c", permission=ToolPermission.READ_ONLY)
def gemini_flash_search_6545c(query: str) -> str:
    """Fast web search for authoritative UK regulatory guidance (FCA, MoneyHelper, gov.uk, UK Finance).

    Args:
        query (str): Search query, optionally scoped with site: filters such as site:fca.org.uk.
    Returns:
        str: Summarised search results with source links.
    """
    return ""


@tool(name="gemini_pro_search_39a85", permission=ToolPermission.READ_ONLY)
def gemini_pro_search_39a85(query: str) -> str:
    """Deep web search for detailed UK regulatory analysis (MCOB 13, Consumer Duty, FG21/1, Mortgage Charter).

    Args:
        query (str): Search query, optionally scoped with site: filters such as site:fca.org.uk.
    Returns:
        str: Detailed search results with source links.
    """
    return ""
