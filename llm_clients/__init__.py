from .mistral_client import MistralClient
from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient

CLIENTS = {
    "Mistral": MistralClient,
    "OpenAI": OpenAIClient,
    "Anthropic": AnthropicClient,
}
