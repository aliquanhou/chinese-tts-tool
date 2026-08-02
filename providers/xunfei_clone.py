"""讯飞一句话复刻（多风格版）Provider

API 文档: https://www.xfyun.cn/doc/spark/voiceclone.html
定价:
  - 按训练次数 + 合成字符数计费
  - 控制台可领取免费测试量
  - 训练成功音色长期有效，不收取存储费用
  - 音频要求: ≤40秒, wav/mp3/m4a/pcm, 单通道, ≥24kHz, 16bit

功能:
  - 一句话克隆 → 多语种合成 (中/英/日/韩/俄/法/阿/西 8语种)
  - 30+ 风格调节 (happy/sad/chat/孙梧空/小猪佩奇...)
  - 方言支持 (粤语/天津/东北/四川/合肥)
  - 多音字指定、静音插入
"""

import base64
import hashlib
import hmac
import json
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

import requests
import websocket

from .clone_base import BaseCloneProvider, CloneVoice


class XunfeiCloneProvider(BaseCloneProvider):
    """讯飞一句话复刻（多风格版）

    训练流程:
      获取 Token → 上传音频 + 创建任务 → 轮询状态 → 获得 res_id → WebSocket 合成

    特点:
    - 只需一句话即可克隆
    - 30+ 种说话风格
    - 8 个语种输出
    - 双向流式通信（适合 LLM 场景）
    """

    _AUTH_TOKEN_URL = "http://avatar-hci.xfyousheng.com/aiauth/v1/token"
    _TRAIN_SUBMIT_URL = (
        "http://opentrain.xfyousheng.com/voice_train/task/submitWithAudio"
    )
    _TRAIN_RESULT_URL = "http://opentrain.xfyousheng.com/voice_train/task/result"
    _SYNTH_WS_URL = "ws://cn-huabei-1.xf-yun.com/v1/private/voice_clone"

    SUPPORTED_FORMATS = ["wav", "mp3", "m4a", "pcm"]
    MAX_AUDIO_DURATION = 40  # 秒
    MAX_AUDIO_SIZE = 3 * 1024 * 1024  # 3 MB

    # 30+ 风格
    STYLES = {
        "normal": "正常",
        "happy": "高兴",
        "sad": "悲伤",
        "angry": "生气",
        "chat": "聊天",
        "story": "讲故事",
        "news": "新闻播报",
        "ad": "广告",
        "sunwukong": "孙悟空",
        "peiqi": "小猪佩奇",
        "robot": "机器人",
        "sweet": "甜美",
        "cold": "冷漠",
    }

    # 方言
    DIALECTS = {
        "yueyu": "粤语",
        "tianjin": "天津话",
        "dongbei": "东北话",
        "sichuan": "四川话",
        "hefei": "合肥话",
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        cfg = config.get("xunfei", {})
        self.app_id = cfg.get("app_id", "")
        self.api_key = cfg.get("api_key", "")
        self.api_secret = cfg.get("api_secret", "")
        self._auth_token = None
        self._token_expires_at = 0

    @property
    def provider_name(self) -> str:
        return "讯飞声音复刻"

    @property
    def supported_formats(self) -> List[str]:
        return self.SUPPORTED_FORMATS

    @property
    def max_audio_duration(self) -> int:
        return self.MAX_AUDIO_DURATION

    # ─── 鉴权 ───────────────────────────────────────────────

    def _get_auth_token(self) -> str:
        """获取讯飞声音复刻鉴权 Token (有效期 7200 秒)"""
        if self._auth_token and time.time() < self._token_expires_at:
            return self._auth_token

        if not self.app_id or not self.api_key:
            raise ValueError(
                "请先在 config.yaml 中配置讯飞的 app_id, api_key, api_secret\n"
                "获取方式: https://console.xfyun.cn/ -> 我的应用"
            )

        timestamp = str(int(time.time()))
        body = {
            "business": {
                "appid": self.app_id,
                "appkey": self.api_key,
                "timestamp": timestamp,
            }
        }
        body_str = json.dumps(body)

        # MD5(appKey + timestamp) → keySign
        key_sign = hashlib.md5(
            (self.api_key + timestamp).encode("utf-8")
        ).hexdigest()

        # MD5(keySign + body) → signature
        signature = hashlib.md5(
            (key_sign + body_str).encode("utf-8")
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "Authorization": signature,
        }

        resp = requests.post(
            self._AUTH_TOKEN_URL, json=body, headers=headers, timeout=15
        )
        result = resp.json()

        if result.get("message") == "success" and result.get("token"):
            self._auth_token = result["token"]
            self._token_expires_at = time.time() + 7000  # 提前 200 秒过期
            return self._auth_token
        else:
            raise RuntimeError(f"获取讯飞 Token 失败: {result}")

    def _train_headers(self, body_str: str = "") -> Dict[str, str]:
        """生成训练接口请求头"""
        x_time = str(int(time.time() * 1000))
        md5_body = hashlib.md5(body_str.encode("utf-8")).hexdigest()
        x_sign = hashlib.md5(
            (self.api_key + x_time + md5_body).encode("utf-8")
        ).hexdigest()

        return {
            "X-AppId": self.app_id,
            "X-Token": self._get_auth_token(),
            "X-Time": x_time,
            "X-Sign": x_sign,
        }

    # ─── 创建克隆音色 ────────────────────────────────────────

    def create_voice(
        self,
        audio_path: str,
        voice_name: str,
        text_id: str = "5001",
        callback_url: str = "",
        **kwargs,
    ) -> CloneVoice:
        """上传音频并创建克隆音色（训练）

        Args:
            audio_path: 参考音频 (≤40秒, wav/mp3/m4a/pcm)
            voice_name: 音色名称
            text_id: 训练文本 ID，5001 为默认一句话复刻
            callback_url: 训练完成回调地址 (可选)

        Returns:
            CloneVoice 含 voice_id (res_id/assetId)
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        if audio_file.stat().st_size > self.MAX_AUDIO_SIZE:
            raise ValueError(
                f"音频文件过大 ({audio_file.stat().st_size / 1024 / 1024:.1f}MB)，"
                f"最大允许 3MB"
            )

        print(f"[讯飞复刻] 正在创建克隆任务: {voice_name} ...")

        # 构建 multipart/form-data
        body_data = {"displayName": voice_name, "textId": text_id}
        if callback_url:
            body_data["callbackUrl"] = callback_url

        headers = self._train_headers(json.dumps(body_data))
        # 移除 Content-Type 让 requests 自动设置 multipart boundary
        headers.pop("Content-Type", None)

        resp = requests.post(
            self._TRAIN_SUBMIT_URL,
            data=body_data,
            files={"file": (audio_file.name, audio_file.read_bytes())},
            headers=headers,
            timeout=120,
        )

        result = resp.json()
        code = result.get("code", -1)

        if code != 0:
            raise RuntimeError(
                f"讯飞创建任务失败 [code={code}]: {result.get('message', result)}"
            )

        task_id = result.get("data", {}).get("taskId", "")
        if not task_id:
            raise RuntimeError(f"未获取到 taskId: {result}")

        print(f"[讯飞复刻] 任务已创建 taskId={task_id}，等待训练完成...")

        # 轮询训练状态
        res_id = self._poll_training(task_id)

        clone_voice = CloneVoice(
            voice_id=res_id,
            name=voice_name,
            provider="xunfei_clone",
            metadata={
                "task_id": task_id,
                "text_id": text_id,
                "source_audio": str(audio_path),
                "provider_display": "讯飞声音复刻",
            },
        )
        self._voice_cache[res_id] = clone_voice
        self._save_cache()

        print(f"[讯飞复刻] ✓ 克隆成功! res_id={res_id}")
        return clone_voice

    def _poll_training(self, task_id: str, timeout: int = 300, interval: int = 3) -> str:
        """轮询训练状态直到完成

        Returns:
            res_id (assetId) — 合成用的音色 ID
        """
        started_at = time.time()

        while time.time() - started_at < timeout:
            body = {"taskId": task_id}
            body_str = json.dumps(body)
            headers = self._train_headers(body_str)

            resp = requests.post(
                self._TRAIN_RESULT_URL,
                json=body,
                headers=headers,
                timeout=15,
            )
            result = resp.json()

            code = result.get("code", -1)
            if code != 0:
                raise RuntimeError(
                    f"查询训练状态失败 [code={code}]: {result.get('message', result)}"
                )

            data = result.get("data", {})
            train_status = data.get("trainStatus", -1)

            if train_status == 1:  # 训练成功
                asset_id = data.get("assetId", "")
                if not asset_id:
                    raise RuntimeError(f"训练完成但未获取到 assetId: {data}")
                return asset_id
            elif train_status == 0:  # 失败
                failed_desc = data.get("failedDesc", "未知原因")
                raise RuntimeError(f"训练失败: {failed_desc}")
            elif train_status in (-1, 2):  # 训练中 / 排队中
                status_text = "训练中..." if train_status == -1 else "排队等待..."
                elapsed = int(time.time() - started_at)
                print(f"[讯飞复刻] {status_text} (已等待 {elapsed}s)")
                time.sleep(interval)
            else:
                raise RuntimeError(f"未知训练状态: trainStatus={train_status}")

        raise TimeoutError(f"训练超时 ({timeout}s)，请稍后手动查询 taskId={task_id}")

    # ─── 合成 ───────────────────────────────────────────────

    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Optional[str] = None,
        style: str = "normal",
        speed: int = 50,
        volume: int = 50,
        pitch: int = 50,
        dialect: str = "",
        **kwargs,
    ) -> str:
        """使用克隆音色通过 WebSocket 合成语音

        Args:
            text: 文本 (≤2000字符)
            voice_id: 克隆音色 res_id (assetId)
            output_path: 输出路径
            style: 风格 (normal/happy/sad/chat/story/news 等30+种)
            speed: 语速 0-100
            volume: 音量 0-100
            pitch: 音调 0-100
            dialect: 方言 (yueyu/tianjin/dongbei/sichuan/hefei)
        """
        if not self.app_id or not self.api_key or not self.api_secret:
            raise ValueError(
                "请先在 config.yaml 中配置讯飞的密钥"
            )

        if output_path is None:
            timestamp = int(time.time() * 1000)
            output_path = str(
                Path(self.config.get("output", {}).get("directory", "./output"))
                / f"xunfei_clone_{voice_id}_{timestamp}.mp3"
            )

        # 构建 WebSocket URL (带签名)
        ws_url = self._build_synth_url()

        # 构建请求体
        request_body = {
            "common": {"app_id": self.app_id},
            "business": {
                "aue": "lame",
                "sfl": 1,
                "vcn": "x6_clone",      # 克隆合成固定值
                "res_id": voice_id,      # 训练得到的音色 ID
                "speed": speed,
                "volume": volume,
                "pitch": pitch,
                "style": style,
            },
            "data": {
                "status": 2,
                "text": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
            },
        }

        if dialect:
            request_body["business"]["dialect"] = dialect

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
                        f"合成错误 [code={code}]: {result.get('message', '')}"
                    )
                    return

                data = result.get("data", {})
                audio_b64 = data.get("audio", "")
                if audio_b64:
                    audio_chunks.append(base64.b64decode(audio_b64))

                if data.get("status") == 2:  # 合成结束
                    ws.close()
            except json.JSONDecodeError:
                pass

        def on_error(ws, error):
            error_msg.append(f"WebSocket 错误: {error}")

        ws_app = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
        )
        ws_app.run_forever()

        if error_msg:
            raise RuntimeError(error_msg[0])

        if not audio_chunks:
            raise RuntimeError("未收到音频数据")

        audio_data = b"".join(audio_chunks)
        Path(output_path).write_bytes(audio_data)

        print(
            f"[讯飞复刻] ✓ 克隆音色合成成功 -> {output_path} "
            f"(大小: {len(audio_data)/1024:.1f}KB)"
        )
        return output_path

    def _build_synth_url(self) -> str:
        """构建带签名的 WebSocket 合成 URL"""
        # 使用与普通 TTS 相同的签名方式
        from datetime import datetime, timezone

        host = "cn-huabei-1.xf-yun.com"
        path = "/v1/private/voice_clone"

        gmt_date = datetime.now(timezone.utc).strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )

        signature_origin = "\n".join(
            [f"host: {host}", f"date: {gmt_date}", f"GET {path} HTTP/1.1"]
        )

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
            "host": host,
        }

        return f"ws://{host}{path}?{urlencode(params)}"

    # ─── 管理 ───────────────────────────────────────────────

    def list_voices(self) -> List[CloneVoice]:
        """列出已克隆的音色"""
        return list(self._voice_cache.values())

    def delete_voice(self, voice_id: str) -> bool:
        """从本地缓存删除音色"""
        if voice_id in self._voice_cache:
            del self._voice_cache[voice_id]
            self._save_cache()
            print(f"[讯飞复刻] 已从本地删除音色: {voice_id}")
            return True
        return False

    def get_available_styles(self) -> list:
        """返回支持的风格列表"""
        return [{"id": k, "description": v} for k, v in self.STYLES.items()]

    def get_available_dialects(self) -> list:
        """返回支持的方言列表"""
        return [{"id": k, "description": v} for k, v in self.DIALECTS.items()]
