"""Agno model factory — construct the right model object for a given provider."""


def create_model(provider: str, model_id: str, api_key: str = ""):
    """Create an Agno model instance.

    Args:
        provider: "google", "anthropic", or "openai"
        model_id: Model identifier (e.g., "gemini-2.0-flash", "claude-sonnet-4-5")
        api_key: API key for the provider
    """
    kwargs = {"id": model_id}
    if api_key:
        kwargs["api_key"] = api_key

    if provider == "google":
        from agno.models.google import Gemini
        return Gemini(**kwargs)
    elif provider == "anthropic":
        from agno.models.anthropic import Claude
        return Claude(**kwargs)
    elif provider == "openai":
        from agno.models.openai import OpenAIResponses
        return OpenAIResponses(**kwargs)
    else:
        raise ValueError(f"Unknown Agno model provider: {provider}")
