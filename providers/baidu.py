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

    # 全部音色 (75个) — 基础/精品/臻品/大模型
    VOICES = {
        # ── 基础音库 (免费额度覆盖) ──
        0: "度小美 — 标准女主播 (基础)",
        1: "度小宇 — 亲切男声 (基础)",
        3: "度逍遥 — 情感男声 (基础)",
        4: "度丫丫 — 可爱童声 (基础)",
        # ── 精品音库 ──
        5003: "度逍遥 — 情感男声 (精品)",
        5118: "度小鹿 — 甜美女声 (精品)",
        106: "度博文 — 专业男主播 (精品)",
        103: "度米朵 — 可爱童声 (精品)",
        110: "度小童 — 童声主播 (精品)",
        111: "度小萌 — 软萌妹子 (精品)",
        5: "度小娇 — 成熟女主播 (精品)",
        # ── 臻品音库 (42个) 高保真仿真人 ──
        4003: "度逍遥 — 情感男声 (臻品)",
        4106: "度博文 — 专业男主播 (臻品)",
        4115: "度小贤 — 电台男主播 (臻品) ⭐",
        5147: "度常盈 — 电台女主播 (臻品) ⭐",
        5976: "度小皮 — 萌娃童声 (臻品)",
        5971: "度皮特 — 老外男声 (臻品)",
        4164: "度阿肯 — 主播男声 (臻品)",
        4176: "度有为 — 磁性男声 (臻品) ⭐",
        4259: "度小新 — 播音女声 (臻品)",
        4119: "度小鹿 — 甜美女声 (臻品)",
        4105: "度灵儿 — 清澈女声 (臻品) ⭐",
        4117: "度小乔 — 活泼女声 (臻品)",
        4288: "度晴岚 — 甜美女声 (臻品)",
        4192: "度青川 — 温柔男声 (臻品)",
        4100: "度小雯 — 活力女主播 (臻品)",
        4103: "度米朵 — 可爱女声 (臻品)",
        4144: "度姗姗 — 娱乐女声 (臻品)",
        4278: "度小贝 — 知识女主播 (臻品)",
        4143: "度清风 — 配音男声 (臻品)",
        4140: "度小新 — 专业女主播 (臻品)",
        4129: "度小彦 — 知识男主播 (臻品)",
        4149: "度星河 — 广告男声 (臻品)",
        4254: "度小清 — 广告女声 (臻品)",
        4206: "度博文 — 综艺男声 (臻品)",
        4147: "度云朵 — 可爱童声 (臻品)",
        4141: "度婉婉 — 甜美女声 (臻品)",
        4226: "南方 — 电台女主播 (臻品)",
        6205: "度悠然 — 旁白男声 (臻品)",
        6221: "度云萱 — 旁白女声 (臻品)",
        6546: "度清豪 — 逍遥侠客 (臻品)",
        6602: "度清柔 — 温柔男神 (臻品)",
        6562: "度雨楠 — 元气少女 (臻品)",
        6543: "度雨萌 — 邻家女孩 (臻品)",
        6747: "度书古 — 情感男声 (臻品)",
        6748: "度书严 — 沉稳男声 (臻品)",
        6746: "度书道 — 沉稳男声 (臻品)",
        6644: "度书宁 — 亲和女声 (臻品)",
        4148: "度小夏 — 甜美女声 (臻品)",
        4277: "西贝 — 脱口秀女声 (臻品)",
        4114: "阿龙 — 说书男声 (臻品)",
        5153: "度常悦 — 民生女主播 (臻品)",
        6561: "度小乐 — 可爱童声 (臻品)",
        # ── 大模型音库 (23个) 超拟人 🔥 ──
        4189: "度涵竹 — 开朗女声 6情感 (大模型·超拟人) 🔥",
        4194: "度嫣然 — 活泼女声 5情感 (大模型·超拟人) 🔥",
        4193: "度泽言 — 开朗男声 4情感 (大模型·超拟人) 🔥",
        4195: "度怀安 — 磁性男声 4情感 (大模型·超拟人) 🔥",
        4196: "度清影 — 甜美女声 4情感 (大模型·超拟人) 🔥",
        4197: "度沁遥 — 知性女声 6情感 (大模型·超拟人) 🔥",
        4179: "度泽言 — 温暖男声 (大模型·超拟人)",
        4146: "度禧禧 — 阳光女声 (大模型·超拟人)",
        6567: "度小柔 — 温柔女声 (大模型·超拟人)",
        4156: "度言浩 — 年轻男声 (大模型·超拟人)",
        4157: "度言静 — 明亮女声 (大模型·超拟人)",
        # ── 大模型方言 (12个) ──
        20100: "度小粤 — 粤语女声 (大模型·方言)",
        20101: "度晓芸 — 粤语女声 (大模型·方言)",
        4257: "四川小哥 — 四川男声 (大模型·方言)",
        4132: "度阿闽 — 闽南男声 (大模型·方言)",
        4139: "度小蓉 — 四川女声 (大模型·方言)",
        5977: "台媒女声 — 台湾女声 (大模型·方言)",
        4007: "度小台 — 台湾女声 (大模型·方言)",
        4150: "度湘玉 — 陕西女声 (大模型·方言)",
        4134: "度阿锦 — 东北女声 (大模型·方言)",
        4172: "度筱林 — 天津女声 (大模型·方言)",
        5980: "度阿花 — 上海女声 (大模型·方言)",
        4154: "度老崔 — 北京男声 (大模型·方言)",
    }

    # 大模型超拟人音色 per 值集合 (支持情感参数)
    EMOTION_VOICES = {4189, 4194, 4193, 4195, 4196, 4197}

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
