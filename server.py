#!/usr/bin/env python3
"""TTS Web UI — Flask 后端服务"""

import io
import sys
import time
import tempfile
import traceback
from pathlib import Path

# UTF-8 stdout
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import yaml

from providers import PROVIDERS, CLONE_PROVIDERS

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


@app.route("/clone")
def clone_page():
    return render_template("clone.html")


# ============================================================
# 音色克隆 API 路由
# ============================================================


@app.route("/api/clone/providers")
def api_clone_providers():
    """返回支持音色克隆的服务商"""
    config = get_config()
    result = []
    for name, cls in CLONE_PROVIDERS.items():
        try:
            p = cls(config)
            result.append(
                {
                    "id": name,
                    "name": p.provider_name,
                    "supported_formats": p.supported_formats,
                    "max_audio_duration": p.max_audio_duration,
                    "has_emotions": hasattr(p, "get_available_emotions"),
                    "has_styles": hasattr(p, "get_available_styles"),
                    "has_dialects": hasattr(p, "get_available_dialects"),
                }
            )
        except Exception as e:
            result.append({"id": name, "name": name, "error": str(e)})
    return jsonify({"providers": result})


@app.route("/api/clone/voices")
def api_clone_voices():
    """列出已克隆的音色"""
    provider_name = request.args.get("provider", "baidu_clone")
    if provider_name not in CLONE_PROVIDERS:
        return jsonify({"error": f"不支持的服务商: {provider_name}"}), 400

    config = get_config()
    try:
        p = CLONE_PROVIDERS[provider_name](config)
        voices = p.list_voices()
        # 也获取风格/情感/方言列表
        extras = {}
        if hasattr(p, "get_available_emotions"):
            extras["emotions"] = p.get_available_emotions()
        if hasattr(p, "get_available_styles"):
            extras["styles"] = p.get_available_styles()
        if hasattr(p, "get_available_dialects"):
            extras["dialects"] = p.get_available_dialects()

        return jsonify(
            {
                "provider": provider_name,
                "name": p.provider_name,
                "voices": [v.to_dict() for v in voices],
                **extras,
            }
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/clone/create", methods=["POST"])
def api_clone_create():
    """创建克隆音色 (上传参考音频)"""
    provider_name = request.form.get("provider", "baidu_clone")
    voice_name = (request.form.get("voice_name") or "").strip()

    if not voice_name:
        return jsonify({"error": "请输入音色名称"}), 400
    if provider_name not in CLONE_PROVIDERS:
        return jsonify({"error": f"不支持的服务商: {provider_name}"}), 400

    # 检查音频文件
    if "audio" not in request.files:
        return jsonify({"error": "请上传参考音频文件"}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"error": "请选择音频文件"}), 400

    # 保存临时文件
    ext = Path(audio_file.filename).suffix or ".wav"
    tmp_path = Path(tempfile.gettempdir()) / f"tts_clone_upload_{int(time.time())}{ext}"
    audio_file.save(str(tmp_path))

    config = get_config()
    try:
        p = CLONE_PROVIDERS[provider_name](config)

        kwargs = {}
        # 可选参数
        lang = request.form.get("lang")
        if lang:
            kwargs["lang"] = lang
        style = request.form.get("style")
        if style:
            kwargs["style"] = style

        clone_voice = p.create_voice(
            audio_path=str(tmp_path),
            voice_name=voice_name,
            **kwargs,
        )

        # 清理临时文件
        try:
            tmp_path.unlink()
        except Exception:
            pass

        return jsonify(
            {
                "success": True,
                "voice": clone_voice.to_dict(),
                "message": f"音色 '{voice_name}' 克隆成功!",
            }
        )
    except Exception as e:
        traceback.print_exc()
        try:
            tmp_path.unlink()
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500


@app.route("/api/clone/synthesize", methods=["POST"])
def api_clone_synthesize():
    """使用克隆音色合成语音"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "请提供 JSON 请求体"}), 400

    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "请输入要合成的文本"}), 400

    voice_id = data.get("voice_id")
    if not voice_id:
        return jsonify({"error": "请指定克隆音色 ID"}), 400

    provider_name = data.get("provider", "baidu_clone")
    if provider_name not in CLONE_PROVIDERS:
        return jsonify({"error": f"不支持的服务商: {provider_name}"}), 400

    config = get_config()
    try:
        p = CLONE_PROVIDERS[provider_name](config)

        kwargs = {
            "speed": data.get("speed", 50),
            "volume": data.get("volume", 50),
            "pitch": data.get("pitch", 50),
        }

        # 可选: 情感 / 风格 / 方言
        emotion = data.get("emotion")
        if emotion:
            kwargs["emotion"] = emotion
        style = data.get("style")
        if style:
            kwargs["style"] = style
        dialect = data.get("dialect")
        if dialect:
            kwargs["dialect"] = dialect

        ext = data.get("format", "mp3")
        timestamp = int(time.time() * 1000)
        filename = f"tts_clone_{provider_name}_{voice_id}_{timestamp}.{ext}"
        output_path = str(OUTPUT_DIR / filename)

        result_path = p.synthesize(
            text=text,
            voice_id=voice_id,
            output_path=output_path,
            **kwargs,
        )

        file_size = Path(result_path).stat().st_size

        return jsonify(
            {
                "success": True,
                "filename": Path(result_path).name,
                "path": result_path,
                "size": file_size,
                "size_kb": round(file_size / 1024, 1),
                "provider": provider_name,
                "provider_name": p.provider_name,
            }
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/clone/voice/<voice_id>", methods=["DELETE"])
def api_clone_delete(voice_id):
    """删除克隆音色"""
    provider_name = request.args.get("provider", "baidu_clone")
    if provider_name not in CLONE_PROVIDERS:
        return jsonify({"error": f"不支持的服务商: {provider_name}"}), 400

    config = get_config()
    try:
        p = CLONE_PROVIDERS[provider_name](config)
        ok = p.delete_voice(voice_id)
        return jsonify({"success": ok, "message": "已删除" if ok else "音色不存在"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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

    # 讯飞超拟人专用参数
    oral_level = data.get("oral_level")
    if oral_level:
        kwargs["oral_level"] = oral_level
    scene = data.get("scene")
    if scene is not None:
        kwargs["scene"] = scene

    # 生成唯一文件名
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
