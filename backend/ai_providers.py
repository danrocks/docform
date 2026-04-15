from abc import ABC, abstractmethodfrom typing import Dict, Type, Anyclass AIProvider(ABC):    """Minimal provider API: one call() method like _call_gemini."""    @abstractmethod    def call(self, prompt: str, *, mode: str = "document", **kwargs) -> Dict[str, Any]:        """        mode: 'document' -> return {'bytes': b'...', 'filename': 'x.docx'}              'template' -> return {'template': {...}}
        """
        raise NotImplementedError

_PROVIDERS: Dict[str, Type[AIProvider]] = {}

def register_provider(name: str):
    def _decorator(cls: Type[AIProvider]):
        _PROVIDERS[name] = cls
        return cls
    return _decorator

def get_provider(name: str, **init_kwargs) -> AIProvider:
    try:
        cls = _PROVIDERS[name]
    except KeyError:
        raise ValueError(f"Unknown AI provider: {name}")
    return cls(**init_kwargs)