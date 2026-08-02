# 中文 TTS 工具 (Chinese TTS Tool)

多服务商中文语音合成命令行工具，支持火山引擎(豆包)、讯飞、百度 — 覆盖从免费到廉价付费的全场景。

## 服务商对比

| 服务商 | 免费额度 | 付费价格 | 音质 | 接入方式 |
|--------|---------|---------|------|---------|
| **火山引擎(豆包)** | 无 | ¥100/百万字 (大厂最低) | ⭐⭐⭐⭐⭐ | REST API |
| **讯飞开放平台** | 500次/天 | 基础发音人免费 | ⭐⭐⭐⭐ | WebSocket |
| **百度智能云** | 5万次/180天(个人) | 基础: ¥12/万次 | ⭐⭐⭐ | REST API |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥

编辑 `config.yaml`，填入你要使用的服务商的 API 密钥：

```yaml
default_provider: volcano  # 默认使用火山引擎

volcano:
  app_id: "your_volcano_app_id"
  access_token: "your_volcano_token"
```

#### 获取密钥:

- **火山引擎**: https://console.volcengine.com/ → 语音技术 → 创建应用
- **讯飞**: https://console.xfyun.cn/ → 创建应用 → 语音合成
- **百度**: https://console.bce.baidu.com/ → 语音技术 → 创建应用

### 3. 使用

```bash
# 基本合成
python tts.py synthesize -t "你好世界，这是一个测试"

# 使用讯飞免费额度
python tts.py synthesize -t "你好世界" -p xunfei

# 指定发音人
python tts.py synthesize -t "你好" -p baidu -v 0

# 从文件合成
python tts.py synthesize -f script.txt -o output.mp3

# 列出所有发音人
python tts.py voices

# 对比各服务商效果
python tts.py compare -t "今天天气真好"

# 只对比讯飞和百度
python tts.py compare -t "测试" -p xunfei,baidu
```

## 可用发音人

### 火山引擎 (volcano)
- `zh_female_qingxin` — 清新女声 ⭐推荐
- `zh_female_tianmei` — 甜美女声
- `zh_male_wenrou` — 温柔男声
- `zh_female_zhixing` — 知性女声
- `zh_male_chunhou` — 醇厚男声
- 更多通过 `python tts.py voices -p volcano` 查看

### 讯飞 (xunfei) — 全部免费
- `xiaoqian` — 小倩 (台湾女声) ⭐推荐
- `xiaoyan` — 小燕 (青年女声)
- `xiaoping` — 小萍 (知性女声)
- `xiaojing` — 小婧 (温柔女声)
- `xuxiaobao` — 许小宝 (可爱童声)

### 百度 (baidu)
- `0` — 度小美 (标准女声) ⭐推荐
- `1` — 度小宇 (标准男声)
- `3` — 度逍遥 (情感男声)
- `4` — 度丫丫 (可爱童声)
- `5118` — 度小鹿 (甜美女声, 精品)

## 作为 Python 库使用

```python
import yaml
from providers import PROVIDERS

with open("config.yaml") as f:
    config = yaml.safe_load(f)

# 使用火山引擎
provider = PROVIDERS["volcano"](config)
path = provider.synthesize("你好世界", speed_ratio=1.0)

# 使用讯飞 (免费)
provider = PROVIDERS["xunfei"](config)
path = provider.synthesize("你好世界", speed=50)

# 使用百度
provider = PROVIDERS["baidu"](config)
path = provider.synthesize("你好世界", voice_person=0)
```

## 项目结构

```
tts-tool/
├── tts.py              # CLI 主入口
├── config.yaml          # 配置文件
├── requirements.txt     # 依赖
├── providers/
│   ├── __init__.py      # Provider 注册
│   ├── base.py          # 抽象基类
│   ├── volcano.py       # 火山引擎
│   ├── xunfei.py        # 讯飞
│   └── baidu.py         # 百度
├── output/              # 输出目录
└── README.md
```

## 常见问题

**Q: 哪个最便宜?**
A: 讯飞每天 500 次免费，完全够个人使用。付费场景火山引擎 ¥100/百万字最便宜。

**Q: 哪个音质最好?**
A: 火山引擎豆包语音大模型效果最好，讯飞次之。

**Q: 文本长度限制?**
A: 火山引擎建议单次 ≤ 1000 字，讯飞 ≤ 2000 汉字，百度 ≤ 500 汉字 (单次)。

## License

MIT
