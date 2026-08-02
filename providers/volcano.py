"""火山引擎 (豆包语音) TTS Provider

API 文档: https://www.volcengine.com/docs/6561/79820
定价: 普通版 ¥100/百万字 (大厂最低)
"""

import json
import time
import uuid
from pathlib import Path
from typing import Optional, Any, Dict

import requests

from .base import BaseTTSProvider


class VolcanoTTSProvider(BaseTTSProvider):
    """火山引擎语音合成服务

    特点:
    - 大厂中长文本最低单价 ¥100/百万字
    - 豆包大模型驱动，仿真人效果好
    - 支持流式和非流式合成
    """

    # 可用音色 — 标准 + 豆包大模型 BV 系列
    VOICES = {
        # ── 基础音色 (免费) ──
        "zh_female_qingxin": "清新女声 — 通用 (基础)",
        "zh_female_tianmei": "甜美女声 — 通用 (基础)",
        "zh_male_wenrou": "温柔男声 — 通用 (基础)",
        "zh_female_shuangkuaidale": "爽快大大咧咧女声 (基础)",
        "zh_male_chunhou": "醇厚男声 (基础)",
        "zh_female_zhixing": "知性女声 (基础)",
        "zh_female_wenjing": "文静女声 (基础)",
        "zh_male_shengdan": "圣诞男声 (基础)",
        "zh_female_xiaoqian": "小倩-北京话 (基础)",
        "zh_male_zhubo": "男主播 (基础)",
        "zh_female_xiaoyue": "小悦-东北话 (基础)",
        # ── 豆包语音大模型 2.0 仿真人 ⭐推荐 ──
        "BV700_V2_streaming": "灿灿 2.0 — 超拟真甜美女声 ⭐",
        "BV705_streaming": "炀炀 — 阳光开朗女声 ⭐",
        "BV001_streaming": "通用女声 — 大模型仿真人 ⭐",
        "BV002_streaming": "通用男声 — 大模型仿真人 ⭐",
        # ── 豆包语音大模型 — 风格化仿真人 ──
        "BV123_streaming": "阳光青年 — 青春向上",
        "BV120_streaming": "反卷青年 — 慵懒随性",
        "BV119_streaming": "通用赘婿 — 网文旁白",
        "BV115_streaming": "古风少御 — 古装女声",
        "BV107_streaming": "霸气青叔 — 沉稳大叔",
        "BV100_streaming": "质朴青年 — 自然男声",
        "BV104_streaming": "温柔淑女 — 温婉女声",
        "BV004_streaming": "开朗青年 — 活泼男声",
        "BV113_streaming": "甜宠少御 — 娇柔女声",
        "BV102_streaming": "儒雅青年 — 斯文男声",
        "BV007_streaming": "亲切女声 — 亲和力女声",
        "BV009_streaming": "知性女声 — 成熟知性",
        "BV008_streaming": "亲切男声 — 亲和力男声",
        "BV419_streaming": "诚诚 — 童声男孩",
        "BV415_streaming": "童童 — 可爱童声",
        "BV158_streaming": "智慧老者 — 老年智者",
        "BV157_streaming": "慈爱姥姥 — 慈祥老人",
        "BV142_streaming": "沉稳解说男 — 纪录片解说",
        "BV143_streaming": "潇洒青年 — 豪迈男声",
        "BV159_streaming": "纨绔青年 — 痞气青年",
        "BV428_streaming": "清新文艺女声 — 文艺范",
        "BV403_streaming": "鸡汤女声 — 治愈系",
        "BV426_streaming": "懒小羊 — 慵懒萌音",
        # ── 场景化仿真人 ──
        "BV411_streaming": "影视解说小帅 🔥 — 抖音电影解说",
        "BV437_streaming": "解说小帅-多情感 🔥 — 多情感版小帅",
        "BV412_streaming": "影视解说小美 🔥 — 女声电影解说",
        "BV418_streaming": "直播一姐 — 带货直播女声",
        "BV410_streaming": "活力解说男 — 体育赛事解说",
        "BV408_streaming": "译制片男声 — 外语配音风格",
        "BV405_streaming": "甜美小源 — 少女可爱音",
        "BR001_streaming": "说唱小哥 — 嘻哈风格rap",
    }

    # 支持的音频格式
    ENCODINGS = ["mp3", "wav", "ogg", "pcm", "opus"]

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        cfg = config.get("volcano", {})
        self.app_id = cfg.get("app_id", "")
        self.access_token = cfg.get("access_token", "")
        self.voice_type = cfg.get("voice_type", "zh_female_qingxin")
        self.encoding = cfg.get("encoding", "mp3")
        self._base_url = "https://openspeech.bytedance.com/api/v1/tts"

    @property
    def provider_name(self) -> str:
        return "火山引擎(豆包语音)"

    @property
    def estimated_cost_per_char(self) -> float:
        # ¥100 / 1,000,000 字 = ¥0.0001/字
        return 0.0001

    def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice_type: Optional[str] = None,
        encoding: Optional[str] = None,
        speed_ratio: float = 1.0,
        volume_ratio: float = 1.0,
        pitch_ratio: float = 1.0,
        **kwargs,
    ) -> str:
        """调用火山引擎 REST API 合成语音

        Args:
            text: 文本内容 (建议每次不超过 1000 字以获得最低延迟)
            output_path: 输出路径
            voice_type: 音色
            encoding: 音频格式
            speed_ratio: 语速 (0.5 - 2.0)
            volume_ratio: 音量 (0.1 - 3.0)
            pitch_ratio: 音调 (0.5 - 2.0)
        """
        if not self.app_id or not self.access_token:
            raise ValueError(
                "请先在 config.yaml 中配置火山引擎的 app_id 和 access_token\n"
                "获取方式: https://console.volcengine.com/ -> 语音技术 -> 创建应用"
            )

        voice = voice_type or self.voice_type
        enc = encoding or self.encoding

        if output_path is None:
            timestamp = int(time.time() * 1000)
            output_path = str(self.output_dir / f"volcano_{timestamp}.{enc}")

        payload = {
            "app": {
                "appid": self.app_id,
                "token": self.access_token,
                "cluster": "volcano_tts",
            },
            "user": {"uid": "tts_tool_user"},
            "audio": {
                "voice_type": voice,
                "encoding": enc,
                "speed_ratio": speed_ratio,
                "volume_ratio": volume_ratio,
                "pitch_ratio": pitch_ratio,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": "query",
                "with_frontend": 1,
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer; {self.access_token}",
        }

        try:
            resp = requests.post(
                self._base_url,
                json=payload,
                headers=headers,
                timeout=60,
            )

            if resp.status_code == 200:
                # 返回结构可能是 JSON (含 base64 音频) 或直接是二进制
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    result = resp.json()
                    # 检查是否包含 base64 编码的音频数据
                    audio_data = result.get("data") or result.get("audio")
                    if audio_data:
                        import base64

                        audio_bytes = base64.b64decode(audio_data)
                        Path(output_path).write_bytes(audio_bytes)
                    elif result.get("code", 0) != 0:
                        raise RuntimeError(
                            f"API 返回错误: {result.get('message', result)}"
                        )
                    else:
                        raise RuntimeError(f"Unexpected JSON response: {result}")
                else:
                    # 直接是二进制音频数据
                    Path(output_path).write_bytes(resp.content)

                print(f"[火山引擎] ✓ 合成成功 -> {output_path}")
                return output_path
            else:
                raise RuntimeError(
                    f"API 请求失败 [{resp.status_code}]: {resp.text[:500]}"
                )

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"网络请求失败: {e}")

    def get_available_voices(self) -> list:
        return [{"id": k, "description": v} for k, v in self.VOICES.items()]

    def get_cost_estimate(self, text: str) -> str:
        """估算本次合成的费用"""
        char_count = len(text)
        cost = char_count * self.estimated_cost_per_char
        return (
            f"文本长度: {char_count} 字 | "
            f"预估费用: {cost:.4f}元 "
            f"({'极低' if cost < 0.01 else '约 ' + str(round(cost, 4)) + ' 元'})"
        )
