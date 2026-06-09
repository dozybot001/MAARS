"""Agno model factory - construct model objects for non-executor stages."""


def create_model(provider: str, model_id: str, api_key: str = ""):
    """Create an Agno model instance.

    Args:
        provider: "openai" or "anthropic"
        model_id: Model identifier (e.g., "gpt-5.5", "claude-sonnet-4-5")
        api_key: API key for the provider
    """
    kwargs = {"id": model_id}
    if api_key:
        kwargs["api_key"] = api_key

    if provider == "openai":
        from agno.models.openai import OpenAIResponses
        return OpenAIResponses(**kwargs)
    elif provider == "anthropic":
        from agno.models.anthropic import Claude
        return Claude(**kwargs)
    else:
        raise ValueError(f"Unknown Agno model provider: {provider}")
