"""讯飞超拟人语音合成 Provider

API 文档: https://www.xfyun.cn/doc/spark/超拟⼈合成.html
定价: 控制台可领取免费测试量，后续按字符计费

特色:
  - 大模型驱动的超拟人合成，效果远超普通 TTS
  - 自动生成拟声词(笑声/叹气等)，更加真实
  - 口语化等级可调 (high/mid/low)
  - 6种场景模式 (散文/小说/新闻/广告/交互)
  - 3个 x4_ 大模型超拟人音色
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any, Dict
from urllib.parse import urlencode

import websocket

from .base import BaseTTSProvider


class XunfeiUltraProvider(BaseTTSProvider):
    """讯飞超拟人语音合成 (WebSocket API)

    与普通在线合成的区别:
    - 大模型生成拟声词，音频更拟人更真实
    - 支持口语化等级: high/mid/low
    - 支持场景选择: 散文/小说/新闻/广告/交互
    - 音色仅 3 个但质量远高于普通合成
    """

    HOST = "cbm01.cn-huabei-1.xf-yun.com"
    DEFAULT_PATH = "/v1/private/mcd9m97e6"

    # 超拟人大模型音色
    # 注意: 需在控制台「发音人管理」中添加后才能使用
    # x5_ 系列为新版超拟人音色
    VOICES = {
        "x5_lingxiaotang_flow": "聆小糖 — 甜美女声 ⭐已授权",
        "x5_lingxiaoxuan_flow": "聆小璇 — 清新女声",
        "x5_lingfeizhe_flow": "聆飞哲 — 阳光男声",
        "x5_lingyuzhao_flow": "聆玉昭 — 温柔女声",
        # x4_ 旧版 (兼容)
        "x4_lingxiaoxuan_oral": "聆小璇 — 旧版女声 (x4)",
        "x4_lingfeizhe_oral": "聆飞哲 — 旧版男声 (x4)",
        "x4_lingyuzhao_oral": "聆玉昭 — 旧版女声 (x4)",
    }

    # 口语化等级
    ORAL_LEVELS = {
        "high": "高 — 大量拟声词,最自然",
        "mid": "中 — 适度拟声词,推荐",
        "low": "低 — 少量拟声词",
    }

    # 场景模式
    SCENES = {
        0: "通用",
        1: "散文 — 抒情朗读",
        2: "小说 — 有声书",
        3: "新闻 — 资讯播报",
        4: "广告 — 营销配音",
        5: "交互 — 对话助手",
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        cfg = config.get("xunfei", {})
        self.app_id = cfg.get("app_id", "")
        self.api_key = cfg.get("api_key", "")
        self.api_secret = cfg.get("api_secret", "")
        self.voice_name = cfg.get("voice_name", "x5_lingxiaotang_flow")
        self.speed = cfg.get("speed", 50)
        self.volume = cfg.get("volume", 50)
        self.pitch = cfg.get("pitch", 50)
        self.oral_level = cfg.get("oral_level", "mid")
        self.scene = cfg.get("scene", 0)
        # 超拟人 API 端点路径 (可在 config.yaml 中覆盖)
        self._api_path = cfg.get("ultra_api_path", self.DEFAULT_PATH)
        self._ws_url = f"wss://{self.HOST}{self._api_path}"

    @property
    def provider_name(self) -> str:
        return "讯飞超拟人"

    @property
    def estimated_cost_per_char(self) -> float:
        return 0.0  # 有免费测试量

    def _build_signed_url(self) -> str:
        """构建带 HMAC-SHA256 签名的 WebSocket URL"""
        gmt_date = datetime.now(timezone.utc).strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )

        signature_origin = "\n".join([
            f"host: {self.HOST}",
            f"date: {gmt_date}",
            f"GET {self._api_path} HTTP/1.1",
        ])

        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()

        signature = base64.b64encode(signature_sha).decode("utf-8")

        authorization_origin = (
            f'api_key="{self.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{signature}"'
        )

        authorization = base64.b64encode(
            authorization_origin.encode("utf-8")
        ).decode("utf-8")

        params = {
            "authorization": authorization,
            "date": gmt_date,
            "host": self.HOST,
        }
        return f"{self._ws_url}?{urlencode(params)}"

    def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice_name: Optional[str] = None,
        speed: Optional[int] = None,
        volume: Optional[int] = None,
        pitch: Optional[int] = None,
        oral_level: Optional[str] = None,
        scene: Optional[int] = None,
        **kwargs,
    ) -> str:
        """超拟人语音合成

        Args:
            text: 文本 (≤2000字符)
            output_path: 输出路径
            voice_name: x4_lingxiaoxuan_oral / x4_lingfeizhe_oral / x4_lingyuzhao_oral
            speed: 语速 0-100
            volume: 音量 0-100
            pitch: 音调 0-100
            oral_level: 口语化等级 high/mid/low
            scene: 场景 0通用/1散文/2小说/3新闻/4广告/5交互
        """
        if not self.app_id or not self.api_key or not self.api_secret:
            raise ValueError(
                "请先在 config.yaml 中配置讯飞的 app_id, api_key, api_secret\n"
                "获取方式: https://console.xfyun.cn/ -> 我的应用\n"
                "需开通「超拟人语音合成」服务"
            )

        vcn = voice_name or self.voice_name
        spd = speed if speed is not None else self.speed
        vol = volume if volume is not None else self.volume
        ptc = pitch if pitch is not None else self.pitch
        oral = oral_level or self.oral_level
        scn = scene if scene is not None else self.scene

        if output_path is None:
            timestamp = int(time.time() * 1000)
            output_path = str(
                self.output_dir / f"xunfei_ultra_{timestamp}.mp3"
            )

        # 文本 Base64 编码
        text_b64 = base64.b64encode(text.encode("utf-8")).decode("utf-8")

        # 构建超拟人请求体
        request_body = {
            "header": {
                "app_id": self.app_id,
                "status": 2,
            },
            "parameter": {
                "oral": {"oral_level": oral},
                "tts": {
                    "vcn": vcn,
                    "audio": {"encoding": "lame"},
                    "speed": spd,
                    "volume": vol,
                    "pitch": ptc,
                    "scn": scn,
                    "rhy": 0,
                },
            },
            "payload": {
                "text": {
                    "encoding": "utf8",
                    "text": text_b64,
                    "status": 2,
                }
            },
        }

        url = self._build_signed_url()
        audio_chunks = []
        error_msg = []

        def on_open(ws):
            ws.send(json.dumps(request_body))

        def on_message(ws, message):
            try:
                result = json.loads(message)
                code = result.get("header", {}).get("code", -1)
                if code != 0:
                    error_msg.append(
                        f"超拟人合成错误 [code={code}]: "
                        f"{result.get('header', {}).get('message', '')}"
                    )
                    return

                payload = result.get("payload", {})
                audio_data = payload.get("audio", {})
                audio_b64 = audio_data.get("audio", "")
                if audio_b64:
                    audio_chunks.append(base64.b64decode(audio_b64))

                # status=2 表示结束
                if audio_data.get("status") == 2:
                    ws.close()
            except json.JSONDecodeError:
                pass

        def on_error(ws, error):
            error_msg.append(f"WebSocket 错误: {error}")

        print(
            f"[讯飞超拟人] 正在合成 (音色={vcn}, 口语化={oral}, 场景={scn})..."
        )

        ws_app = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
        )
        ws_app.run_forever()

        if error_msg:
            raise RuntimeError(error_msg[0])

        if not audio_chunks:
            raise RuntimeError("未收到音频数据，请检查超拟人服务是否已开通")

        audio_data = b"".join(audio_chunks)
        Path(output_path).write_bytes(audio_data)

        print(
            f"[讯飞超拟人] ✓ 合成成功 -> {output_path} "
            f"(大小: {len(audio_data)/1024:.1f}KB)"
        )
        return output_path

    def get_available_voices(self) -> list:
        return [{"id": k, "description": v} for k, v in self.VOICES.items()]

    def get_oral_levels(self) -> list:
        return [{"id": k, "description": v} for k, v in self.ORAL_LEVELS.items()]

    def get_scenes(self) -> list:
        return [{"id": k, "description": v} for k, v in self.SCENES.items()]
