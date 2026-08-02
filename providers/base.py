"""TTS Provider 抽象基类"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any


class BaseTTSProvider(ABC):
    """所有 TTS 服务商必须实现的接口"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_dir = Path(config.get("output", {}).get("directory", "./output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def synthesize(self, text: str, output_path: Optional[str] = None, **kwargs) -> str:
        """
        将文本合成为语音文件

        Args:
            text: 要合成的文本
            output_path: 输出文件路径 (可选，默认自动生成)
            **kwargs: 额外的合成参数 (voice, speed, volume 等)

        Returns:
            生成的音频文件路径
        """
        ...

    @abstractmethod
    def get_available_voices(self) -> list:
        """返回可用的发音人列表"""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """服务商名称"""
        ...

    @property
    @abstractmethod
    def estimated_cost_per_char(self) -> float:
        """预估的每字符成本 (元)"""
        ...
