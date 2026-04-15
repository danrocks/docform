from abc import ABC, abstractmethod 
from typing import Dict, Type, Any 

import asyncio  
  
class AIProvider(ABC):  
    """Minimal provider API: one call() method like _call_gemini."""  
  
    @abstractmethod  
    def call(self, prompt: str, *, mode: str = "document", **kwargs) -> Dict[str, Any]:  
        raise NotImplementedError  
  
    async def acall(self, prompt: str, *, mode: str = "document", **kwargs) -> Dict[str, Any]:  
        """Async version. Default wraps call() in a thread. Override for native async."""  
        return await asyncio.run_in_executor(None, lambda: self.call(prompt, mode=mode, **kwargs))

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