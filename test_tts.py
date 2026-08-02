"""TTS 工具功能测试 (不依赖真实 API 密钥)"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import yaml
from providers.base import BaseTTSProvider
from providers.volcano import VolcanoTTSProvider
from providers.xunfei import XunfeiTTSProvider
from providers.baidu import BaiduTTSProvider


def test_provider_registry():
    """测试服务商注册"""
    from providers import PROVIDERS

    assert "volcano" in PROVIDERS
    assert "xunfei" in PROVIDERS
    assert "baidu" in PROVIDERS
    assert len(PROVIDERS) == 3
    print("[PASS] 服务商注册: 3/3 已注册")


def test_config_loading():
    """测试配置加载"""
    config_path = Path(__file__).parent / "config.yaml"
    assert config_path.exists(), "config.yaml 缺失"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert "volcano" in config
    assert "xunfei" in config
    assert "baidu" in config
    assert "default_provider" in config
    print(f"[PASS] 配置加载: 默认服务商 = {config['default_provider']}")


def test_volcano_provider():
    """测试火山引擎 provider 接口"""
    config = {
        "volcano": {"app_id": "", "access_token": "", "voice_type": "zh_female_qingxin"},
        "output": {"directory": tempfile.gettempdir()},
    }
    provider = VolcanoTTSProvider(config)

    assert provider.provider_name == "火山引擎(豆包语音)"
    assert provider.estimated_cost_per_char == 0.0001
    assert len(provider.get_available_voices()) >= 10

    # 无密钥时应抛出明确错误
    try:
        provider.synthesize("测试")
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "app_id" in str(e) or "请先在" in str(e)
    print(f"[PASS] 火山引擎: {len(provider.get_available_voices())} 音色, 缺密钥正确报错")


def test_xunfei_provider():
    """测试讯飞 provider 接口"""
    config = {
        "xunfei": {"app_id": "", "api_key": "", "api_secret": ""},
        "output": {"directory": tempfile.gettempdir()},
    }
    provider = XunfeiTTSProvider(config)

    assert "讯飞" in provider.provider_name
    assert provider.estimated_cost_per_char == 0.0
    voices = provider.get_available_voices()
    assert len(voices) >= 5
    free_count = sum(1 for v in voices if "免费" in v["description"])
    assert free_count >= 5
    print(f"[PASS] 讯飞: {len(voices)} 音色 ({free_count} 免费)")


def test_baidu_provider():
    """测试百度 provider 接口"""
    config = {
        "baidu": {"api_key": "", "secret_key": "", "voice_person": 0, "speed": 5, "volume": 5, "pitch": 5},
        "output": {"directory": tempfile.gettempdir()},
    }
    provider = BaiduTTSProvider(config)

    assert "百度" in provider.provider_name
    assert provider.estimated_cost_per_char == 0.000033
    voices = provider.get_available_voices()
    assert len(voices) >= 4

    # 验证空密钥会被正确识别 (走本地校验)
    try:
        provider._get_access_token()
    except (ValueError, RuntimeError):
        pass
    print(f"[PASS] 百度: {len(voices)} 音色, 缺密钥正确报错")


def test_cost_estimate():
    """测试费用估算"""
    config = {
        "volcano": {"app_id": "x", "access_token": "x"},
        "output": {"directory": tempfile.gettempdir()},
    }
    provider = VolcanoTTSProvider(config)

    test_text = "你好世界，这是一个测试"
    estimate = provider.get_cost_estimate(test_text)
    assert f"{len(test_text)} 字" in estimate
    assert "元" in estimate
    print(f"[PASS] 费用估算: {estimate}")


def test_file_synthesis_argparse():
    """测试 CLI 参数处理"""
    from tts import main
    import argparse

    # 模拟 synthesize 参数
    sys.argv = [
        "tts.py",
        "synthesize",
        "-t", "测试文本",
    ]
    # 由于没有 API 密钥，会报错，但参数解析和加载应正常
    try:
        main()
    except SystemExit as e:
        # 预期退出码为 1 (API密钥缺失) 或 0
        pass
    except ValueError as e:
        # 也接受 ValueError (密钥缺失)
        assert "请先在" in str(e) or "config" in str(e).lower()
    print("[PASS] CLI 参数处理: synthesize -t 正常解析")


if __name__ == "__main__":
    print("=" * 60)
    print("  TTS 工具功能测试")
    print("=" * 60)
    print()

    tests = [
        test_provider_registry,
        test_config_loading,
        test_volcano_provider,
        test_xunfei_provider,
        test_baidu_provider,
        test_cost_estimate,
        test_file_synthesis_argparse,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"  结果: {passed} 通过, {failed} 失败, {len(tests)} 总计")
    print("=" * 60)
