"""讯飞开放平台 TTS Provider

API 文档: https://www.xfyun.cn/doc/tts/online_tts/API.html
定价:
  - 免费额度: 500次/天 (基础发音人)
  - 特色发音人: ¥20,000/年
  - 免费发音人: 小燕、小倩、小萍、小婧、许小宝
"""

import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any, Dict
from urllib.parse import urlencode

import websocket

from .base import BaseTTSProvider


class XunfeiTTSProvider(BaseTTSProvider):
    """讯飞在线语音合成 (WebSocket API)

    特点:
    - 每天免费 500 次调用
    - 基础发音人完全免费
    - 中文语音合成效果业界领先
    """

    # 免费基础发音人
    FREE_VOICES = {
        "xiaoyan": "小燕 - 青年女声 (免费)",
        "xiaoqian": "小倩 - 台湾女声 (免费, 推荐)",
        "xiaoping": "小萍 - 知性女声 (免费)",
        "xiaojing": "小婧 - 温柔女声 (免费)",
        "xuxiaobao": "许小宝 - 可爱童声 (免费)",
    }

    # 付费特色发音人 (¥20,000/年)
    PREMIUM_VOICES = {
        "xiaoqi": "小琪 - 甜美女声 (付费)",
        "xiaomei": "小梅 - 粤语女声 (付费)",
        "xiaoqian": "小倩 - 台湾女声 (付费)",
    }

    HOST = "tts-api.xfyun.cn"
    WS_URL = f"wss://{HOST}/v2/tts"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        cfg = config.get("xunfei", {})
        self.app_id = cfg.get("app_id", "")
        self.api_key = cfg.get("api_key", "")
        self.api_secret = cfg.get("api_secret", "")
        self.voice_name = cfg.get("voice_name", "xiaoqian")
        self.speed = cfg.get("speed", 50)
        self.volume = cfg.get("volume", 50)
        self.pitch = cfg.get("pitch", 50)

    @property
    def provider_name(self) -> str:
        return "讯飞开放平台"

    @property
    def estimated_cost_per_char(self) -> float:
        # 基础发音人免费 (500次/天)
        # 超出后按调用次数计费，非按字符
        return 0.0

    def _build_auth_url(self) -> str:
        """构建带鉴权签名的 WebSocket URL

        使用 HMAC-SHA256 签名方式
        """
        # RFC1123 格式时间
        gmt_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

        # 签名原文: host\ndate\nGET /v2/tts HTTP/1.1
        signature_origin = "\n".join(
            [f"host: {self.HOST}", f"date: {gmt_date}", "GET /v2/tts HTTP/1.1"]
        )

        # HMAC-SHA256 签名
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()

        signature = base64.b64encode(signature_sha).decode("utf-8")

        # 拼接 authorization_origin
        authorization_origin = (
            f'api_key="{self.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{signature}"'
        )

        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
            "utf-8"
        )

        # 构建带鉴权参数的 URL
        params = {
            "authorization": authorization,
            "date": gmt_date,
            "host": self.HOST,
        }

        return f"{self.WS_URL}?{urlencode(params)}"

    def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice_name: Optional[str] = None,
        speed: Optional[int] = None,
        volume: Optional[int] = None,
        pitch: Optional[int] = None,
        **kwargs,
    ) -> str:
        """通过 WebSocket 调用讯飞语音合成

        Args:
            text: 文本内容 (最大约 2000 汉字)
            output_path: 输出路径
            voice_name: 发音人
            speed: 语速 (0-100)
            volume: 音量 (0-100)
            pitch: 音调 (0-100)
        """
        if not self.app_id or not self.api_key or not self.api_secret:
            raise ValueError(
                "请先在 config.yaml 中配置讯飞的 app_id, api_key, api_secret\n"
                "获取方式: https://console.xfyun.cn/ 创建应用 -> 语音合成"
            )

        voice = voice_name or self.voice_name
        spd = speed if speed is not None else self.speed
        vol = volume if volume is not None else self.volume
        ptc = pitch if pitch is not None else self.pitch

        if output_path is None:
            timestamp = int(time.time() * 1000)
            output_path = str(self.output_dir / f"xunfei_{timestamp}.mp3")

        # 文本 Base64 编码
        text_b64 = base64.b64encode(text.encode("utf-8")).decode("utf-8")

        # 构建请求体
        request_body = {
            "common": {"app_id": self.app_id},
            "business": {
                "aue": "lame",  # mp3 格式
                "sfl": 1,       # 开启流式返回
                "vcn": voice,
                "tte": "utf8",
                "speed": spd,
                "volume": vol,
                "pitch": ptc,
            },
            "data": {"status": 2, "text": text_b64},  # status=2 一次性传输
        }

        # 使用鉴权方式一 (x-api-key) 更简单
        url = self.WS_URL
        audio_chunks = []
        error_msg = []

        def on_open(ws):
            ws.send(json.dumps(request_body))

        def on_message(ws, message):
            try:
                result = json.loads(message)
                code = result.get("code", -1)
                if code != 0:
                    error_msg.append(
                        f"API 错误 [code={code}]: {result.get('message', 'unknown')}"
                    )
                    return

                data = result.get("data", {})
                audio_b64 = data.get("audio", "")
                if audio_b64:
                    chunk = base64.b64decode(audio_b64)
                    audio_chunks.append(chunk)

                # status=2 表示合成结束
                if data.get("status") == 2:
                    ws.close()

            except json.JSONDecodeError:
                pass  # 可能是二进制帧

        def on_error(ws, error):
            error_msg.append(f"WebSocket 错误: {error}")

        # 尝试方式一: x-api-key 鉴权
        ws_app = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            header={"x-api-key": self.api_key},
        )

        ws_app.run_forever()

        if error_msg:
            # 如果 x-api-key 失败，尝试签名方式
            if "401" in str(error_msg) or "11200" in str(error_msg) or "10005" in str(error_msg[0]):
                # 重试用签名鉴权
                audio_chunks = []
                error_msg.clear()
                signed_url = self._build_auth_url()
                ws_app = websocket.WebSocketApp(
                    signed_url,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                )
                ws_app.run_forever()

        if error_msg:
            raise RuntimeError(error_msg[0])

        if not audio_chunks:
            raise RuntimeError("未收到任何音频数据，请检查 API 配额和配置")

        # 合并音频片段写入文件
        audio_data = b"".join(audio_chunks)
        Path(output_path).write_bytes(audio_data)

        duration_s = len(audio_data) / 16000  # 估算时长 (16kHz mp3)
        print(f"[讯飞] ✓ 合成成功 -> {output_path} " f"(大小: {len(audio_data)/1024:.1f}KB, 约{duration_s:.1f}秒)")
        return output_path

    def get_available_voices(self) -> list:
        voices = [{"id": k, "description": v} for k, v in self.FREE_VOICES.items()]
        voices += [{"id": k, "description": v} for k, v in self.PREMIUM_VOICES.items()]
        return voices
