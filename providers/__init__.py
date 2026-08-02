from .base import BaseTTSProvider
from .volcano import VolcanoTTSProvider
from .xunfei import XunfeiTTSProvider
from .baidu import BaiduTTSProvider
from .clone_base import BaseCloneProvider, CloneVoice
from .baidu_clone import BaiduCloneProvider
from .xunfei_clone import XunfeiCloneProvider
from .xunfei_ultra import XunfeiUltraProvider

__all__ = [
    "BaseTTSProvider",
    "VolcanoTTSProvider",
    "XunfeiTTSProvider",
    "BaiduTTSProvider",
    "XunfeiUltraProvider",
    "BaseCloneProvider",
    "CloneVoice",
    "BaiduCloneProvider",
    "XunfeiCloneProvider",
]

# TTS Provider registry
PROVIDERS = {
    "volcano": VolcanoTTSProvider,
    "xunfei": XunfeiTTSProvider,
    "xunfei_ultra": XunfeiUltraProvider,
    "baidu": BaiduTTSProvider,
}

# Clone Provider registry
CLONE_PROVIDERS = {
    "baidu_clone": BaiduCloneProvider,
    "xunfei_clone": XunfeiCloneProvider,
}
