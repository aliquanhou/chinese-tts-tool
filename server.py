#!/usr/bin/env python3
"""TTS Web UI — Flask 后端服务"""

import io
import sys
import traceback
from pathlib import Path

# UTF-8 stdout
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import yaml

from providers import PROVIDERS

app = Flask(__name__)
CORS(app)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 加载配置
CONFIG_PATH = Path(__file__).parent / "config.yaml"
_config_cache = None
_config_mtime = 0


def get_config():
    global _config_cache, _config_mtime
    mtime = CONFIG_PATH.stat().st_mtime if CONFIG_PATH.exists() else 0
    if _config_cache is None or mtime != _config_mtime:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f)
        _config_mtime = mtime
    return _config_cache


def get_provider(provider_name=None):
    config = get_config()
    name = provider_name or config.get("default_provider", "volcano")
    if name not in PROVIDERS:
        return None
    return PROVIDERS[name](config), name


# ============================================================
# 页面路由
# ============================================================


@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# API 路由
# ============================================================


@app.route("/api/providers")
def api_providers():
    """返回所有服务商及其元信息"""
    config = get_config()
    result = []
    for name, cls in PROVIDERS.items():
        try:
            p = cls(config)
            voices = p.get_available_voices()
            free_voices = sum(1 for v in voices if "免费" in str(v.get("description", "")))
            result.append(
                {
                    "id": name,
                    "name": p.provider_name,
                    "voices": voices,
                    "free_count": free_voices,
                    "cost_per_char": p.estimated_cost_per_char,
                    "cost_label": "免费" if p.estimated_cost_per_char == 0 else f"{p.estimated_cost_per_char}元/字",
                    "highlight": name == config.get("default_provider"),
                }
            )
        except Exception as e:
            result.append(
                {"id": name, "name": name, "voices": [], "error": str(e)}
            )
    return jsonify({"providers": result, "default": config.get("default_provider")})


@app.route("/api/voices")
def api_voices():
    """返回指定服务商的发音人列表"""
    provider_name = request.args.get("provider", "volcano")
    config = get_config()
    if provider_name not in PROVIDERS:
        return jsonify({"error": f"不支持的服务商: {provider_name}"}), 400

    p = PROVIDERS[provider_name](config)
    return jsonify(
        {
            "provider": provider_name,
            "name": p.provider_name,
            "voices": p.get_available_voices(),
            "cost_per_char": p.estimated_cost_per_char,
        }
    )


@app.route("/api/synthesize", methods=["POST"])
def api_synthesize():
    """合成语音"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "请提供 JSON 请求体"}), 400

    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "请输入要合成的文本"}), 400

    provider_name = data.get("provider", "volcano")
    if provider_name not in PROVIDERS:
        return jsonify({"error": f"不支持的服务商: {provider_name}"}), 400

    config = get_config()
    try:
        provider = PROVIDERS[provider_name](config)
    except Exception as e:
        return jsonify({"error": f"初始化服务商失败: {e}"}), 500

    # 构建合成参数
    kwargs = {}
    voice = data.get("voice")
    if voice:
        kwargs["voice_name"] = voice
        kwargs["voice_type"] = voice
        try:
            kwargs["voice_person"] = int(voice)
        except (ValueError, TypeError):
            pass

    speed = data.get("speed")
    if speed is not None:
        kwargs["speed"] = speed
        kwargs["speed_ratio"] = speed / 50.0

    volume = data.get("volume")
    if volume is not None:
        kwargs["volume"] = volume
        kwargs["volume_ratio"] = volume / 50.0

    pitch = data.get("pitch")
    if pitch is not None:
        kwargs["pitch"] = pitch

    # 生成唯一文件名
    import time
    timestamp = int(time.time() * 1000)
    ext = data.get("format", "mp3")
    filename = f"tts_{provider_name}_{timestamp}.{ext}"
    output_path = str(OUTPUT_DIR / filename)

    try:
        result_path = provider.synthesize(text, output_path=output_path, **kwargs)
        file_size = Path(result_path).stat().st_size

        # 费用估算
        cost_info = None
        if hasattr(provider, "get_cost_estimate"):
            cost_info = provider.get_cost_estimate(text)

        return jsonify(
            {
                "success": True,
                "filename": Path(result_path).name,
                "path": result_path,
                "size": file_size,
                "size_kb": round(file_size / 1024, 1),
                "cost": cost_info,
                "provider": provider_name,
                "provider_name": provider.provider_name,
            }
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/audio/<filename>")
def api_audio(filename):
    """提供音频文件下载"""
    # 安全检查，防止路径穿越
    safe_name = Path(filename).name
    file_path = OUTPUT_DIR / safe_name
    if not file_path.exists():
        return jsonify({"error": "文件不存在"}), 404
    return send_file(
        file_path,
        mimetype="audio/mpeg" if safe_name.endswith(".mp3") else "audio/wav",
        as_attachment=False,
    )


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    """查看或更新配置"""
    if request.method == "GET":
        config = get_config()
        # 返回配置概览（隐藏 API 密钥）
        safe_config = {}
        for k, v in config.items():
            if isinstance(v, dict):
                safe_config[k] = {
                    kk: ("***" if "key" in kk.lower() or "secret" in kk.lower() or "token" in kk.lower() else vv)
                    for kk, vv in v.items()
                }
            else:
                safe_config[k] = v
        return jsonify(safe_config)

    if request.method == "POST":
        data = request.get_json()
        if not data:
            return jsonify({"error": "请提供配置数据"}), 400

        provider = data.get("provider")
        if not provider:
            return jsonify({"error": "请指定服务商 (provider 字段)"}), 400

        config = get_config()
        if provider not in config:
            config[provider] = {}

        for field in data.get("fields", {}):
            config[provider][field] = data["fields"][field]

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

        # 清除缓存
        global _config_cache
        _config_cache = None
        return jsonify({"success": True, "message": f"{provider} 配置已更新"})


if __name__ == "__main__":
    print("=" * 60)
    print("  中文 TTS Web UI")
    print("=" * 60)
    config = get_config()
    print(f"  默认服务商: {config.get('default_provider', 'volcano')}")
    print(f"  输出目录:   {OUTPUT_DIR.resolve()}")
    print()
    print("  打开浏览器访问: http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
