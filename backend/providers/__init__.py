# package initializer: import modules so they register themselves
from . import gemini  # noqa: F401
from . import openai  # noqa: F401
# add new provider modules here as they are created