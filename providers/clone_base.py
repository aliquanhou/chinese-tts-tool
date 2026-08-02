"""音色克隆 Provider 抽象基类

所有音色克隆服务商需实现此接口:
  - create_voice()  上传音频 → 创建克隆音色 → 返回 voice_id
  - synthesize()    使用克隆音色合成语音
  - list_voices()   列出已克隆的音色
  - delete_voice()  删除克隆音色
"""

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List


class CloneVoice:
    """克隆音色数据模型"""

    def __init__(
        self,
        voice_id: str,
        name: str,
        provider: str,
        created_at: float = None,
        metadata: Dict[str, Any] = None,
    ):
        self.voice_id = str(voice_id)
        self.name = name
        self.provider = provider
        self.created_at = created_at or time.time()
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "voice_id": self.voice_id,
            "name": self.name,
            "provider": self.provider,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CloneVoice":
        return cls(
            voice_id=d["voice_id"],
            name=d["name"],
            provider=d["provider"],
            created_at=d.get("created_at"),
            metadata=d.get("metadata", {}),
        )


class BaseCloneProvider(ABC):
    """音色克隆服务商抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._voice_cache: Dict[str, CloneVoice] = {}
        self._cache_file = self._get_cache_path()
        self._load_cache()

    def _get_cache_path(self) -> Path:
        """音色缓存文件路径"""
        output_dir = Path(self.config.get("output", {}).get("directory", "./output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f".clone_voices_{self.provider_name_slug}.json"

    def _load_cache(self):
        """从磁盘加载音色缓存"""
        if self._cache_file.exists():
            try:
                data = json.loads(self._cache_file.read_text(encoding="utf-8"))
                for item in data:
                    v = CloneVoice.from_dict(item)
                    self._voice_cache[v.voice_id] = v
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_cache(self):
        """将音色缓存写入磁盘"""
        data = [v.to_dict() for v in self._voice_cache.values()]
        self._cache_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @abstractmethod
    def create_voice(
        self,
        audio_path: str,
        voice_name: str,
        **kwargs,
    ) -> CloneVoice:
        """
        上传音频并创建克隆音色

        Args:
            audio_path: 参考音频文件路径 (wav/mp3/m4a)
            voice_name: 音色名称 (用户自定义)
            **kwargs: 服务商特定参数

        Returns:
            CloneVoice 对象 (含 voice_id)

        Raises:
            RuntimeError: 训练失败
        """
        ...

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        使用克隆音色合成语音

        Args:
            text: 要合成的文本
            voice_id: 克隆音色 ID
            output_path: 输出文件路径
            **kwargs: 合成参数 (speed, volume, pitch, emotion 等)

        Returns:
            生成的音频文件路径
        """
        ...

    @abstractmethod
    def list_voices(self) -> List[CloneVoice]:
        """返回已克隆的音色列表"""
        ...

    @abstractmethod
    def delete_voice(self, voice_id: str) -> bool:
        """删除克隆音色"""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """服务商名称"""
        ...

    @property
    def provider_name_slug(self) -> str:
        """服务商名称的 URL 友好标识"""
        return self.provider_name.replace(" ", "_").lower()

    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """支持的音频上传格式"""
        ...

    @property
    @abstractmethod
    def max_audio_duration(self) -> int:
        """支持的最大音频时长 (秒)"""
        ...
