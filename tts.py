#!/usr/bin/env python3
"""
中文 TTS 工具 — 多服务商语音合成命令行工具

支持的服务商:
  火山引擎(豆包)  — ¥100/百万字 (付费最低)
  讯飞开放平台    — 500次/天免费
  百度智能云      — 5万次/180天免费 (个人)

用法:
  python tts.py synthesize "你好世界"                    # 使用默认服务商
  python tts.py synthesize "你好" -p volcano             # 指定服务商
  python tts.py synthesize -f input.txt                  # 从文件合成
  python tts.py voices                                   # 列出所有发音人
  python tts.py compare "测试文本"                        # 对比所有服务商效果
"""

import argparse
import io
import sys
from pathlib import Path

import yaml

from providers import PROVIDERS, BaseTTSProvider

# Force UTF-8 stdout on Windows (GBK can't encode emoji/¥)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def load_config(config_path: str = "config.yaml") -> dict:
    """加载 YAML 配置文件"""
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"[错误] 配置文件不存在: {config_path}")
        print("请复制 config.yaml 并根据实际情况填写 API 密钥")
        sys.exit(1)

    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_provider(config: dict, provider_name: str = None) -> BaseTTSProvider:
    """根据配置获取 TTS Provider 实例"""
    name = provider_name or config.get("default_provider", "volcano")

    if name not in PROVIDERS:
        available = ", ".join(PROVIDERS.keys())
        print(f"[错误] 不支持的服务商: {name}")
        print(f"可用服务商: {available}")
        sys.exit(1)

    provider_cls = PROVIDERS[name]
    return provider_cls(config)


def cmd_synthesize(args):
    """合成语音命令"""
    config = load_config(args.config)
    provider = get_provider(config, args.provider)

    # 读取文本
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read().strip()
        if not text:
            print(f"[错误] 文件为空: {args.file}")
            sys.exit(1)
    elif args.text:
        text = args.text
    else:
        print("[错误] 请指定合成文本 (-t) 或输入文件 (-f)")
        sys.exit(1)

    print(f"[信息] 使用服务商: {provider.provider_name}")
    print(f"[信息] 文本内容: {text[:100]}{'...' if len(text) > 100 else ''}")

    # 构建额外参数
    kwargs = {}
    if args.voice:
        # 处理不同类型的 voice 参数
        kwargs["voice_name"] = args.voice
        kwargs["voice_type"] = args.voice
        try:
            kwargs["voice_person"] = int(args.voice)
        except ValueError:
            pass
    if args.speed is not None:
        kwargs["speed"] = args.speed
        kwargs["speed_ratio"] = args.speed / 50.0 if args.speed <= 100 else 1.0
    if args.volume is not None:
        kwargs["volume"] = args.volume
        kwargs["volume_ratio"] = args.volume / 50.0 if args.volume <= 100 else 1.0

    # 显示成本估算 (仅付费服务商)
    if hasattr(provider, "get_cost_estimate"):
        print(f"[费用] {provider.get_cost_estimate(text)}")

    try:
        output_path = provider.synthesize(
            text, output_path=args.output, **kwargs
        )
        print(f"\n✅ 语音合成完成!")
        print(f"   文件: {Path(output_path).resolve()}")
        print(f"   大小: {Path(output_path).stat().st_size / 1024:.1f} KB")
    except Exception as e:
        print(f"\n❌ 合成失败: {e}")
        sys.exit(1)


def cmd_voices(args):
    """列出所有可用发音人"""
    config = load_config(args.config)

    if args.provider:
        # 列出特定服务商
        provider = get_provider(config, args.provider)
        print(f"\n{'='*60}")
        print(f"  {provider.provider_name} — 可用发音人")
        print(f"{'='*60}")
        for v in provider.get_available_voices():
            print(f"  {v['id']:<20} {v['description']}")
        if hasattr(provider, "estimated_cost_per_char"):
            cost = provider.estimated_cost_per_char
            if cost > 0:
                print(f"\n  预估成本: {cost}元/字")
            else:
                print(f"\n  💰 基础发音人完全免费!")
    else:
        # 列出所有服务商
        for name, cls in PROVIDERS.items():
            provider = cls(config)
            print(f"\n{'='*60}")
            print(f"  {provider.provider_name} ({name})")
            print(f"{'='*60}")
            for v in provider.get_available_voices():
                print(f"  {v['id']:<20} {v['description']}")
            if hasattr(provider, "estimated_cost_per_char"):
                cost = provider.estimated_cost_per_char
                if cost > 0:
                    print(f"\n  预估成本: {cost}元/字")
                else:
                    print(f"\n  💰 基础发音人完全免费!")


def cmd_compare(args):
    """对比多个服务商的合成效果"""
    config = load_config(args.config)

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read().strip()
    else:
        text = args.text

    if not text:
        print("[错误] 请指定对比文本 (-t) 或输入文件 (-f)")
        sys.exit(1)

    providers_to_test = args.providers.split(",") if args.providers else list(PROVIDERS.keys())

    print(f"\n{'='*60}")
    print(f"  TTS 效果对比: {text[:50]}{'...' if len(text) > 50 else ''}")
    print(f"{'='*60}\n")

    results = []
    for name in providers_to_test:
        if name.strip() not in PROVIDERS:
            print(f"  ⚠ 跳过未知服务商: {name}")
            continue

        print(f"▶ 正在使用 {name} 合成...", end=" ", flush=True)
        try:
            provider = get_provider(config, name.strip())
            output = provider.synthesize(text)
            results.append((name, provider.provider_name, output, True))
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")
            results.append((name, "N/A", None, False))

    print(f"\n{'='*60}")
    print(f"  对比结果汇总")
    print(f"{'='*60}")
    for name, display_name, path, ok in results:
        status = f"✅ {path}" if ok else "❌ 失败"
        print(f"  {display_name} ({name}): {status}")


def main():
    parser = argparse.ArgumentParser(
        description="中文 TTS 工具 — 多服务商语音合成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本合成
  python tts.py synthesize -t "你好世界，这是一个测试"

  # 指定服务商和发音人
  python tts.py synthesize -t "你好" -p xunfei -v xiaoyan

  # 从文件合成
  python tts.py synthesize -f script.txt -o output.mp3

  # 列出所有发音人
  python tts.py voices
  python tts.py voices -p baidu

  # 对比效果
  python tts.py compare -t "今天天气真好"

服务商对比:
  火山引擎(volcano)  付费最低 ¥100/百万字, 音质好
  讯飞(xunfei)       免费 500次/天, 基础发音人免费
  百度(baidu)        免费 5万次/180天(个人), 接入简单
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # synthesize 子命令
    synth_parser = subparsers.add_parser("synthesize", aliases=["synth", "s"], help="合成语音")
    synth_parser.add_argument("text", nargs="?", help="要合成的文本")
    synth_parser.add_argument("-t", "--text", dest="text_opt", help="要合成的文本 (与位置参数相同)")
    synth_parser.add_argument("-f", "--file", help="从文件读取文本")
    synth_parser.add_argument("-p", "--provider", help="服务商 (volcano/xunfei/baidu)")
    synth_parser.add_argument("-v", "--voice", help="发音人/音色")
    synth_parser.add_argument("-s", "--speed", type=int, help="语速")
    synth_parser.add_argument("--volume", type=int, help="音量")
    synth_parser.add_argument("-o", "--output", help="输出文件路径")
    synth_parser.add_argument("-c", "--config", default="config.yaml", help="配置文件路径")

    # voices 子命令
    voices_parser = subparsers.add_parser("voices", aliases=["v"], help="列出可用发音人")
    voices_parser.add_argument("-p", "--provider", help="指定服务商")
    voices_parser.add_argument("-c", "--config", default="config.yaml", help="配置文件路径")

    # compare 子命令
    compare_parser = subparsers.add_parser("compare", aliases=["cmp"], help="对比服务商效果")
    compare_parser.add_argument("text", nargs="?", help="要对比的文本")
    compare_parser.add_argument("-t", "--text", dest="text_opt", help="要对比的文本")
    compare_parser.add_argument("-f", "--file", help="从文件读取文本")
    compare_parser.add_argument("-p", "--providers", help="服务商列表 (逗号分隔, 默认全部)")
    compare_parser.add_argument("-c", "--config", default="config.yaml", help="配置文件路径")

    args = parser.parse_args()

    # 处理 text 参数的两种传入方式
    if hasattr(args, "text_opt") and args.text_opt:
        args.text = args.text_opt
    if hasattr(args, "text") and not args.text and not getattr(args, "file", None):
        pass  # 保持原样

    if args.command in ("synthesize", "synth", "s"):
        cmd_synthesize(args)
    elif args.command in ("voices", "v"):
        cmd_voices(args)
    elif args.command in ("compare", "cmp"):
        cmd_compare(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
