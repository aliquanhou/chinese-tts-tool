"""百度智能云 TTS Provider

API 文档: https://aca.bce.baidu.com/doc/SPEECH/s/mlbxh7xie
定价:
  - 免费额度 (个人): 基础音库 5万次/180天, 精品音库 2000次/15天
  - 免费额度 (企业): 基础音库 1亿次/180天
  - 基础音库: 预付费最低 12元/万次, 后付费 20元/万次
  - 精品音库: 预付费最低 30元/万次, 后付费 40元/万次
"""

import time
from pathlib import Path
from typing import Optional, Any, Dict
from urllib.parse import quote

import requests

from .base import BaseTTSProvider


class BaiduTTSProvider(BaseTTSProvider):
    """百度智能云短文本语音合成 (REST API)

    特点:
    - 个人认证免费 5万次/180天
    - 企业认证免费 1亿次/180天
    - REST API 接入简单
    - 单次最大 1024 GBK 字节 (约 500 汉字)
    """

    # 基础音库发音人 (免费额度覆盖)
    VOICES = {
        0: "度小美 - 标准女声 (基础, 推荐)",
        1: "度小宇 - 标准男声 (基础)",
        3: "度逍遥 - 情感男声 (基础)",
        4: "度丫丫 - 可爱童声 (基础)",
        # 精品音库
        5003: "度逍遥 - 情感男声 (精品)",
        5118: "度小鹿 - 甜美女声 (精品)",
        106: "度博文 - 新闻男声 (精品)",
        103: "度米朵 - 可爱童声 (精品)",
    }

    # 映射 aue 到文件扩展名
    AUE_MAP = {3: "mp3", 4: "pcm", 5: "pcm", 6: "wav"}

    _TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    _TTS_URL = "https://tsn.baidu.com/text2audio"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        cfg = config.get("baidu", {})
        self.api_key = cfg.get("api_key", "")
        self.secret_key = cfg.get("secret_key", "")
        self.voice_person = cfg.get("voice_person", 0)
        self.speed = cfg.get("speed", 5)
        self.volume = cfg.get("volume", 5)
        self.pitch = cfg.get("pitch", 5)

        # token 缓存
        self._access_token = None
        self._token_expires_at = 0

    @property
    def provider_name(self) -> str:
        return "百度智能云"

    @property
    def estimated_cost_per_char(self) -> float:
        # 后付费基础音库: 20元/万次
        # 每次调用120字节(约60汉字), 即 20元 / (10000 * 60) = 约 0.000033/字
        return 0.000033

    def _get_access_token(self) -> str:
        """获取或刷新百度 access_token (有效期约30天)"""
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
            # 提前5分钟过期
            self._token_expires_at = time.time() + result.get("expires_in", 2592000) - 300
            return self._access_token
        else:
            raise RuntimeError(f"获取百度 access_token 失败: {result}")

    def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice_person: Optional[int] = None,
        speed: Optional[int] = None,
        volume: Optional[int] = None,
        pitch: Optional[int] = None,
        aue: int = 3,  # mp3
        **kwargs,
    ) -> str:
        """调用百度短文本在线语音合成

        Args:
            text: 文本 (最大 1024 GBK 字节, 约 500 汉字)
            output_path: 输出路径
            voice_person: 发音人编号
            speed: 语速 (0-15)
            volume: 音量 (0-15 精品, 0-9 基础)
            pitch: 音调 (0-15)
            aue: 音频格式 3=mp3, 6=wav
        """
        token = self._get_access_token()
        per = voice_person if voice_person is not None else self.voice_person
        spd = speed if speed is not None else self.speed
        vol = volume if volume is not None else self.volume
        pit = pitch if pitch is not None else self.pitch

        if output_path is None:
            ext = self.AUE_MAP.get(aue, "mp3")
            timestamp = int(time.time() * 1000)
            output_path = str(self.output_dir / f"baidu_{timestamp}.{ext}")

        # 构建请求参数
        # tex 需要 2 次 URL 编码
        params = {
            "tex": quote(quote(text, safe=""), safe=""),
            "tok": token,
            "cuid": "tts_tool_baidu",
            "ctp": "1",
            "lan": "zh",
            "per": per,
            "spd": spd,
            "pit": pit,
            "vol": vol,
            "aue": aue,
        }

        try:
            resp = requests.post(
                self._TTS_URL,
                data=params,
                timeout=30,
            )

            content_type = resp.headers.get("Content-Type", "")

            if content_type.startswith("audio"):
                # 合成成功，保存音频
                Path(output_path).write_bytes(resp.content)
                duration_s = len(resp.content) / 16000  # 估算
                print(
                    f"[百度] ✓ 合成成功 -> {output_path} "
                    f"(大小: {len(resp.content)/1024:.1f}KB, 约{duration_s:.1f}秒)"
                )
                return output_path
            else:
                # 返回 JSON 错误
                error = resp.json() if resp.text else {"err_msg": "unknown"}
                raise RuntimeError(
                    f"百度 API 错误 [err_no={error.get('err_no', 'N/A')}]: "
                    f"{error.get('err_msg', 'unknown')}"
                )

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"网络请求失败: {e}")

    def get_available_voices(self) -> list:
        return [{"id": k, "description": v} for k, v in self.VOICES.items()]
