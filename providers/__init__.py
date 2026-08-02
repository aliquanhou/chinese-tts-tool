from .base import BaseTTSProvider
from .volcano import VolcanoTTSProvider
from .xunfei import XunfeiTTSProvider
from .baidu import BaiduTTSProvider

__all__ = [
    "BaseTTSProvider",
    "VolcanoTTSProvider",
    "XunfeiTTSProvider",
    "BaiduTTSProvider",
]

# Provider registry
PROVIDERS = {
    "volcano": VolcanoTTSProvider,
    "xunfei": XunfeiTTSProvider,
    "baidu": BaiduTTSProvider,
}
