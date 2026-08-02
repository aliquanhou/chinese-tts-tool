"""百度大模型声音复刻 Provider

API 文档: https://cloud.baidu.com/doc/SPEECH/s/vm9sbp4z9
定价:
  - 创建音色: 预付费 8元/个, 后付费 8.8元/个
  - 在线合成: 预付费 6.5元/万字符, 后付费 7元/万字符
  - 音频要求: 5-20 秒, wav/mp3/m4a/ogg/aac, ≤5MB
"""

import base64
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

import requests

from .clone_base import BaseCloneProvider, CloneVoice


class BaiduCloneProvider(BaseCloneProvider):
    """百度大模型声音复刻

    特点:
    - 接入最简单: 一个 POST 请求创建音色
    - 音频只需 5-20 秒
    - 支持情感合成 (happy/down/surprise/angry/fear/disgust)
    - 支持方言迁移 (上海/河南/四川/湖南/贵州)
    - 音色 1 年未使用自动删除
    """

    _TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    _CLONE_CREATE_URL = (
        "https://aip.baidubce.com/rest/2.0/speech/publiccloudspeech/v1/voice/clone/create"
    )
    _CLONE_TTS_URL = (
        "https://aip.baidubce.com/rest/2.0/speech/publiccloudspeech/v1/voice/clone/tts"
    )
    _CLONE_LIST_URL = (
        "https://aip.baidubce.com/rest/2.0/speech/publiccloudspeech/v1/voice/clone/list"
    )

    SUPPORTED_FORMATS = ["wav", "mp3", "m4a", "ogg", "aac"]
    MAX_AUDIO_DURATION = 20  # 秒
    MAX_AUDIO_SIZE = 5 * 1024 * 1024  # 5 MB

    EMOTIONS = {
        "neutral": "中性",
        "happy": "高兴",
        "down": "低落",
        "surprise": "惊讶",
        "angry": "生气",
        "fear": "害怕",
        "disgust": "厌恶",
    }

    DIALECTS = {
        "shanghai": "上海话",
        "henan": "河南话",
        "sichuan": "四川话",
        "guizhou": "贵州话",
        "hunan": "湖南话",
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        cfg = config.get("baidu", {})
        self.api_key = cfg.get("api_key", "")
        self.secret_key = cfg.get("secret_key", "")
        self._access_token = None
        self._token_expires_at = 0

    @property
    def provider_name(self) -> str:
        return "百度声音复刻"

    @property
    def supported_formats(self) -> List[str]:
        return self.SUPPORTED_FORMATS

    @property
    def max_audio_duration(self) -> int:
        return self.MAX_AUDIO_DURATION

    def _get_access_token(self) -> str:
        """获取百度 access_token"""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "请先在 config.yaml 中配置百度的 api_key 和 secret_key\n"
                "获取方式: https://console.bce.baidu.com/ -> 语音技术 -> 创建应用"
            )

        resp = requests.post(
            self._TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key,
            },
            timeout=10,
        )
        result = resp.json()
        if "access_token" in result:
            self._access_token = result["access_token"]
            self._token_expires_at = (
                time.time() + result.get("expires_in", 2592000) - 300
            )
            return self._access_token
        else:
            raise RuntimeError(f"获取百度 token 失败: {result}")

    def create_voice(
        self,
        audio_path: str,
        voice_name: str,
        voice_desc: str = "",
        lang: str = "zh",
        audio_url: str = "",
        **kwargs,
    ) -> CloneVoice:
        """上传音频创建克隆音色

        Args:
            audio_path: 音频文件路径 (本地)
            voice_name: 音色名称
            voice_desc: 音色描述
            lang: 语种 (zh / ja)
            audio_url: 如果提供，优先使用 URL 方式

        Returns:
            CloneVoice 对象
        """
        token = self._get_access_token()

        # 检查音频
        if audio_url:
            payload = {"voice_name": voice_name, "audio_url": audio_url, "lang": lang}
        elif audio_path:
            audio_file = Path(audio_path)
            if not audio_file.exists():
                raise FileNotFoundError(f"音频文件不存在: {audio_path}")

            # 检查文件大小
            if audio_file.stat().st_size > self.MAX_AUDIO_SIZE:
                raise ValueError(
                    f"音频文件过大 ({audio_file.stat().st_size / 1024 / 1024:.1f}MB)，"
                    f"最大允许 5MB"
                )

            # Base64 编码音频
            audio_bytes = audio_file.read_bytes()
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            payload = {
                "voice_name": voice_name,
                "audio_file": audio_b64,
                "lang": lang,
            }
        else:
            raise ValueError("请提供 audio_path 或 audio_url")

        if voice_desc:
            payload["voice_desc"] = voice_desc

        print(f"[百度复刻] 正在创建音色: {voice_name} ...")

        resp = requests.post(
            self._CLONE_CREATE_URL,
            params={"access_token": token},
            json=payload,
            timeout=60,
        )

        result = resp.json()
        status = result.get("status")
        message = result.get("message", "")

        if status == 0:
            voice_id = str(result["data"]["voice_id"])
            clone_voice = CloneVoice(
                voice_id=voice_id,
                name=voice_name,
                provider="baidu_clone",
                metadata={
                    "lang": lang,
                    "voice_desc": voice_desc,
                    "source_audio": str(audio_path),
                    "provider_display": "百度声音复刻",
                },
            )
            self._voice_cache[voice_id] = clone_voice
            self._save_cache()

            print(f"[百度复刻] ✓ 音色创建成功! voice_id={voice_id}")
            return clone_voice
        else:
            raise RuntimeError(
                f"百度音色创建失败 [status={status}]: {message}"
            )

    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Optional[str] = None,
        speed: int = 5,
        volume: int = 5,
        pitch: int = 5,
        emotion: str = "",
        dialect: str = "",
        media_type: str = "mp3",
        **kwargs,
    ) -> str:
        """使用克隆音色合成语音

        Args:
            text: 文本 (≤500字符)
            voice_id: 克隆音色 ID
            output_path: 输出路径
            speed: 语速 0-15
            volume: 音量 0-15
            pitch: 音调 0-15
            emotion: 情感 (happy/down/surprise/angry/fear/disgust)
            dialect: 方言 (shanghai/henan/sichuan/guizhou/hunan)
            media_type: wav / mp3
        """
        token = self._get_access_token()

        if output_path is None:
            ext = media_type
            timestamp = int(time.time() * 1000)
            output_path = str(
                Path(self.config.get("output", {}).get("directory", "./output"))
                / f"baidu_clone_{voice_id}_{timestamp}.{ext}"
            )

        payload = {
            "text": text,
            "voice_id": int(voice_id),
            "speed": speed,
            "volume": volume,
            "pitch": pitch,
            "media_type": media_type,
        }

        if emotion:
            if dialect:
                raise ValueError("emotion 和 dialect 不能同时使用")
            payload["emotion"] = emotion

        if dialect:
            if emotion:
                raise ValueError("emotion 和 dialect 不能同时使用")
            payload["dialect"] = dialect

        resp = requests.post(
            self._CLONE_TTS_URL,
            params={"access_token": token},
            json=payload,
            timeout=60,
        )

        content_type = resp.headers.get("Content-Type", "")
        if content_type.startswith("audio"):
            Path(output_path).write_bytes(resp.content)
            size_kb = len(resp.content) / 1024
            print(
                f"[百度复刻] ✓ 克隆音色合成成功 -> {output_path} "
                f"(大小: {size_kb:.1f}KB)"
            )
            return output_path
        else:
            error = resp.json() if resp.text else {"message": "unknown"}
            raise RuntimeError(
                f"百度克隆合成失败 [status={error.get('status')}]: "
                f"{error.get('message', 'unknown')}"
            )

    def list_voices(self) -> List[CloneVoice]:
        """列出已克隆的音色（从缓存 + 尝试服务端查询）"""
        # 从服务端获取最新列表
        try:
            token = self._get_access_token()
            resp = requests.post(
                self._CLONE_LIST_URL,
                params={"access_token": token},
                json={},
                timeout=10,
            )
            result = resp.json()
            if result.get("status") == 0:
                for item in result.get("data", {}).get("voice_list", []):
                    vid = str(item.get("voice_id"))
                    if vid not in self._voice_cache:
                        self._voice_cache[vid] = CloneVoice(
                            voice_id=vid,
                            name=item.get("voice_name", f"voice_{vid}"),
                            provider="baidu_clone",
                            metadata={
                                "voice_desc": item.get("voice_desc", ""),
                                "lang": item.get("lang", "zh"),
                                "provider_display": "百度声音复刻",
                            },
                        )
                self._save_cache()
        except Exception:
            pass  # 网络不通时用缓存

        return list(self._voice_cache.values())

    def delete_voice(self, voice_id: str) -> bool:
        """从缓存中删除音色（百度暂不提供删除 API，仅清理本地）"""
        if voice_id in self._voice_cache:
            del self._voice_cache[voice_id]
            self._save_cache()
            print(f"[百度复刻] 已从本地删除音色: {voice_id}")
            return True
        return False

    def get_available_emotions(self) -> list:
        """返回支持的情感列表"""
        return [{"id": k, "description": v} for k, v in self.EMOTIONS.items()]

    def get_available_dialects(self) -> list:
        """返回支持的方言列表"""
        return [{"id": k, "description": v} for k, v in self.DIALECTS.items()]
