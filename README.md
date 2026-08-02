# 🔊 中文 TTS 工具 (Chinese TTS Tool)

> 多服务商中文语音合成工具 — 命令行 + Web UI 双模式，覆盖从免费到商业的全场景。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen)]()
[![iFlytek](https://img.shields.io/badge/iFlytek-Free%20500%2Fday-orange)]()
[![Baidu](https://img.shields.io/badge/Baidu-Free%2050K%2F180d-blue)]()

---

## 目录

- [5 分钟快速上手](#5-分钟快速上手)
- [服务商对比与选型](#服务商对比与选型)
- [获取 API 密钥（详细图文指引）](#获取-api-密钥)
- [Web UI 使用指南](#web-ui-使用指南)
- [CLI 命令行参考](#cli-命令行参考)
- [Python SDK 编程接口](#python-sdk-编程接口)
- [架构设计](#架构设计)
- [常见问题与排错](#常见问题与排错)
- [贡献指南](#贡献指南)

---

## 5 分钟快速上手

### 前提条件

- Python 3.10+
- 一个 TTS 服务商的 API 密钥（推荐讯飞，免费）

### Step 1：克隆并安装

```bash
git clone https://github.com/aliquanhou/chinese-tts-tool.git
cd chinese-tts-tool
pip install -r requirements.txt
```

### Step 2：配置密钥

```bash
# 从模板复制一份配置
copy config.yaml.example config.yaml   # Windows
# 或
cp config.yaml.example config.yaml     # macOS / Linux
```

编辑 `config.yaml`，填入 API 密钥。以讯飞为例（推荐新手免费体验）：

```yaml
default_provider: xunfei

xunfei:
  app_id: "你的APPID"
  api_key: "你的APIKey"
  api_secret: "你的APISecret"
```

> 💡 密钥从哪来？详见 [获取 API 密钥](#获取-api-密钥)

### Step 3：开始使用

**方式 A — Web UI（推荐）**

```bash
python server.py
# 浏览器打开 http://localhost:5000
```

**方式 B — 命令行**

```bash
python tts.py synthesize -t "你好世界，欢迎使用中文TTS工具"
```

---

## 服务商对比与选型

### 概览

| 维度 | 🥇 讯飞开放平台 | 🥈 火山引擎(豆包) | 🥉 百度智能云 |
|------|:-----------:|:------------:|:--------:|
| **免费额度** | **500 次/天** | 无 | 5 万次/180 天 |
| **付费价格** | 基础免费 | ¥100/百万字 | ¥12/万次 |
| **音质评分** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **接入方式** | WebSocket | REST API | REST API |
| **单次最大文本** | ~2000 汉字 | ~1000 字 | ~500 汉字 |
| **发音人数量** | 5 免费 + 3 付费 | 11 种 | 4 基础 + 4 精品 |
| **适合场景** | 个人/小项目 | 商业/批量生产 | 有免费额度兜底 |

### 选型建议

| 你的情况 | 推荐方案 |
|----------|---------|
| 个人学习、Demo | **讯飞** — 零成本，每天 500 次够用 |
| 创业项目、MVP | **讯飞** 起步 → 量大了切火山引擎 |
| 批量生产、听书 | **火山引擎** — 最低单价 + 最好音质 |
| 企业有百度云账号 | **百度** — 企业认证送 1 亿次免费 |
| 多场景覆盖 | 三个都配，按需切换 |

### 费用实例

| 场景 | 每日用量 | 讯飞 | 火山引擎 | 百度 |
|------|---------|------|---------|------|
| 每日 100 次短句 (20字/次) | 2000 字 | ¥0 (免费) | ¥0.2/天 | ¥0.07/天 |
| 每日 50 段长文 (500字/段) | 2.5 万字 | ¥0 (免费) | ¥2.5/天 | ¥0.8/天 |
| 每月听书级别 | 100 万字 | 需付费 | **¥100/月** | ¥330/月 |

---

## 获取 API 密钥

### 讯飞开放平台（推荐新手）

1. 访问 [讯飞开放平台控制台](https://console.xfyun.cn/)
2. 注册/登录 → 点击「创建新应用」
3. 填写应用名称（如 `tts-tool`），平台选择「WebAPI」
4. 创建完成后，点击「语音合成」→「在线语音合成」→「开通服务」
   - 选择「免费包」（500 次/天）
5. 在应用详情页获取三要素：
   - **APPID**：应用列表可见
   - **APIKey**：应用详情 → 平台信息
   - **APISecret**：应用详情 → 平台信息
6. 将上述值填入 `config.yaml` 的 `xunfei` 段

### 火山引擎（推荐商业用户）

1. 访问 [火山引擎控制台](https://console.volcengine.com/)
2. 注册/登录 → 「语音技术」→「语音合成」
3. 点击「创建应用」→ 填写名称 → 获取 **APPID** 和 **Access Token**
4. 在 [计费页面](https://console.volcengine.com/tts/billing) 开通后付费
5. 将 `app_id` 和 `access_token` 填入 `config.yaml` 的 `volcano` 段

### 百度智能云

1. 访问 [百度智能云控制台](https://console.bce.baidu.com/)
2. 注册/登录 → 「产品服务」→「人工智能」→「语音技术」
3. 创建应用 → 勾选「语音合成」→ 领取免费额度
4. 获取 **API Key** 和 **Secret Key**
5. 填入 `config.yaml` 的 `baidu` 段

---

## Web UI 使用指南

### 启动

```bash
python server.py
```

浏览器打开 **http://localhost:5000**

### 界面功能

```
┌─────────────────────────────────────────────────────────┐
│ 🔊 中文 TTS                              [⚙ 设置]      │
├────────────────────────────┬────────────────────────────┤
│  [火山引擎] [讯飞] [百度]  │   🎧 播放器                 │
│                            │   ┌───────────────────┐    │
│  📝 输入文本               │   │  ▶ 00:00 ━━━━━━   │    │
│  ┌───────────────────────┐│   │  ▁▃▅▇▅▃▁▃▅▇       │    │
│  │ 请输入要转换的文字...   ││   └───────────────────┘    │
│  │                       ││                             │
│  └───────────────────────┘│   📊 文件信息               │
│         120 字             │   大小: 33KB  费用: 免费    │
│                            │   [💾 下载]                │
│  🎤 小倩(推荐)  🎵 MP3   │                             │
│  ⚡语速 ━━━●━━ 50        │   🕓 历史记录               │
│  🔊音量 ━━━●━━ 50        │   讯飞 "你好世界"  04:55   │
│                            │   百度 "测试文本"  04:30   │
│  [▶ 开始合成]             │                             │
│  (Ctrl+Enter 快捷键)      │                             │
└────────────────────────────┴────────────────────────────┘
```

### 操作流程

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1. 选服务商 | 点击顶部 Tab | 免费服务商带 🆓 标识 |
| 2. 输入文本 | 在文本框输入 | 右侧显示实时字数统计 |
| 3. 选发音人 | 下拉菜单切换 | 音色 ID + 描述文字 |
| 4. 调参数 | 拖动语速/音量滑块 | 0-100，默认 50 |
| 5. 合成 | 点击按钮或 Ctrl+Enter | 自动播放，可下载 |
| 6. 查看历史 | 右侧列表点击 | 可回放之前的合成结果 |

### 在线配置 API 密钥

点击右上角 **⚙ 设置** → 弹出表单，直接填入各服务商的密钥 → 保存。

> 配置实时生效，无需重启服务器。

### 音频格式

| 格式 | 推荐场景 | 备注 |
|------|---------|------|
| **MP3** | 通用播放 | 体积小，兼容广 |
| WAV | 专业音频处理 | 无损，文件较大 |

---

## CLI 命令行参考

### 命令总览

```
tts.py <command> [options]

命令:
  synthesize (s)     合成语音
  voices (v)         列出可用发音人
  compare (cmp)      对比多个服务商效果
```

### `synthesize` — 合成语音

```bash
# 基础用法
python tts.py synthesize -t "你好世界"

# 指定服务商
python tts.py synthesize -t "你好" -p xunfei

# 指定发音人
python tts.py synthesize -t "你好" -p xunfei -v xiaoyan
python tts.py synthesize -t "你好" -p baidu -v 0
python tts.py synthesize -t "你好" -p volcano -v zh_male_wenrou

# 调节语速和音量
python tts.py synthesize -t "你好" -s 70 --volume 40

# 从文件读取文本
python tts.py synthesize -f article.txt

# 指定输出路径
python tts.py synthesize -t "你好" -o my_audio.mp3

# 使用快捷别名
python tts.py s -t "你好"    # s = synthesize
```

**参数说明**

| 参数 | 简写 | 类型 | 说明 |
|------|------|------|------|
| `text` | `-t` | string | 要合成的文本 |
| `--file` | `-f` | path | 从文件读取文本 |
| `--provider` | `-p` | string | 服务商: volcano/xunfei/baidu |
| `--voice` | `-v` | string | 发音人 ID |
| `--speed` | `-s` | int | 语速 (0-100) |
| `--volume` | | int | 音量 (0-100) |
| `--output` | `-o` | path | 输出文件路径 |
| `--config` | `-c` | path | 配置文件路径 |

### `voices` — 列出发音人

```bash
# 列出所有服务商的所有发音人
python tts.py voices

# 只看百度
python tts.py voices -p baidu

# 快捷别名
python tts.py v -p xunfei
```

### `compare` — 对比效果

```bash
# 用所有已配服务商合成同一文本
python tts.py compare -t "今天天气真好"

# 只对比指定服务商
python tts.py compare -t "测试文本" -p xunfei,baidu

# 从文件读取对比文本
python tts.py compare -f script.txt
```

---

## Python SDK 编程接口

### 架构

```
providers/
├── base.py       ← BaseTTSProvider  抽象基类（扩展新服务商只需继承它）
├── volcano.py    ← VolcanoTTSProvider  火山引擎实现
├── xunfei.py     ← XunfeiTTSProvider   讯飞实现
└── baidu.py      ← BaiduTTSProvider    百度实现
```

### 基础用法

```python
import yaml
from providers import PROVIDERS

# 1. 加载配置
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# 2. 创建 provider 实例
provider = PROVIDERS["xunfei"](config)

# 3. 合成语音
path = provider.synthesize(
    text="你好世界",
    voice_name="xiaoqian",   # 发音人
    speed=50,                 # 0-100
    volume=50,                # 0-100
    output_path="output.mp3", # 可选
)
print(f"音频已生成: {path}")
```

### 多服务商切换

```python
def tts_factory(provider_name, config):
    """工厂函数：按名称创建 provider"""
    if provider_name not in PROVIDERS:
        raise ValueError(f"不支持: {provider_name}，可选: {list(PROVIDERS.keys())}")
    return PROVIDERS[provider_name](config)

# 按场景选择
tts = tts_factory("volcano", config)  # 商业级音质
tts = tts_factory("xunfei", config)   # 免费
tts = tts_factory("baidu", config)    # 短句场景
```

### 批量合成

```python
from providers import PROVIDERS
import yaml

with open("config.yaml") as f:
    config = yaml.safe_load(f)

tts = PROVIDERS["xunfei"](config)

sentences = [
    "欢迎收听今日新闻。",
    "今天天气晴朗，适合户外活动。",
    "感谢您的收听，我们明天再见。",
]

for i, text in enumerate(sentences):
    path = tts.synthesize(text, output_path=f"output/news_{i:03d}.mp3")
    print(f"[{i+1}/{len(sentences)}] {path}")
```

### 获取服务商信息

```python
provider = PROVIDERS["volcano"](config)

print(f"服务商: {provider.provider_name}")
print(f"成本: {provider.estimated_cost_per_char} 元/字")
print(f"发音人: {len(provider.get_available_voices())} 个")

# 费用估算
print(provider.get_cost_estimate("你好世界"))  # 文本长度: 4 字 | 预估: 0.0004元

# 列出所有音色
for v in provider.get_available_voices():
    print(f"  {v['id']:<25} {v['description']}")
```

### 扩展新服务商

```python
# my_provider.py
from providers.base import BaseTTSProvider

class MyProvider(BaseTTSProvider):
    @property
    def provider_name(self):
        return "我的服务商"

    @property
    def estimated_cost_per_char(self):
        return 0.0001

    def synthesize(self, text, output_path=None, **kwargs):
        # 实现你的 TTS API 调用
        ...

    def get_available_voices(self):
        return [{"id": "voice_1", "description": "标准女声"}]

# 注册
from providers import PROVIDERS
PROVIDERS["my_provider"] = MyProvider
```

### Flask API 接口

启动 `python server.py` 后，也可以通过 HTTP 调用：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/providers` | GET | 列出所有服务商及音色 |
| `/api/voices?provider=xunfei` | GET | 某服务商的发音人列表 |
| `/api/synthesize` | POST | 合成语音 (JSON body) |
| `/api/audio/<filename>` | GET | 下载音频文件 |
| `/api/config` | GET/POST | 查看/更新配置 |

**合成示例**：

```bash
curl -X POST http://localhost:5000/api/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text":"你好世界","provider":"xunfei","voice":"xiaoqian","speed":50,"volume":50}'
```

**响应**：

```json
{
  "success": true,
  "filename": "tts_xunfei_1785704158093.mp3",
  "size_kb": 33.1,
  "provider_name": "讯飞开放平台",
  "cost": "文本长度: 4 字 | 预估费用: 0.0000元 (免费)"
}
```

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────┐
│                   用户界面层                     │
│  ┌──────────────┐  ┌────────────────────────┐   │
│  │   CLI (tts.py)│  │  Web UI (server.py)    │   │
│  │   argparse    │  │  Flask + HTML/CSS      │   │
│  └──────┬───────┘  └───────────┬────────────┘   │
│         │                      │                 │
├─────────┼──────────────────────┼─────────────────┤
│         ▼                      ▼          适配层 │
│  ┌─────────────────────────────────────────┐     │
│  │         Provider Registry               │     │
│  │  volcano │ xunfei │ baidu │ (custom)    │     │
│  └────────────────────┬────────────────────┘     │
│                       │                          │
├───────────────────────┼──────────────────────────┤
│                       ▼                核心抽象  │
│  ┌─────────────────────────────────────────┐     │
│  │        BaseTTSProvider (ABC)            │     │
│  │  synthesize() / voices() / cost         │     │
│  └────────────────────┬────────────────────┘     │
│                       │                          │
├───────────────────────┼──────────────────────────┤
│         ┌─────────────┼─────────────┐    外部API │
│         ▼             ▼             ▼            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ 火山引擎  │ │ 讯飞平台  │ │ 百度智能  │         │
│  │ REST API │ │WebSocket │ │ REST API │         │
│  └──────────┘ └──────────┘ └──────────┘         │
└─────────────────────────────────────────────────┘
```

### 设计原则

| 原则 | 实现 |
|------|------|
| **统一接口** | `BaseTTSProvider` 抽象基类，所有服务商实现同一套 `synthesize()` / `voices()` |
| **可扩展** | 新增服务商只需实现 3 个抽象方法，注册到 `PROVIDERS` 字典 |
| **配置驱动** | `config.yaml` 集中管理所有密钥和参数，支持运行时热更新 |
| **安全第一** | `config.yaml` 已 gitignore，提供 `.example` 模板；密钥通过设置面板在线填写 |
| **双模式** | CLI（自动化/脚本）+ Web UI（人工交互），共享同一套 provider 代码 |

---

## 常见问题与排错

### 安装问题

**Q: pip install 报错 `ModuleNotFoundError: No module named 'websocket'`**

```bash
# 确认 Python 版本
python --version  # 需要 3.10+

# 指定正确的 Python 安装
python -m pip install websocket-client
```

**Q: Windows 下中文输出乱码**

工具已内置 UTF-8 输出重定向。如果仍有问题：

```powershell
chcp 65001  # 控制台切 UTF-8
```

### 密钥问题

**Q: 讯飞返回 `code: 11200 功能未授权`**

- 确认已在讯飞控制台开通「在线语音合成」服务
- 免费包每日 500 次，用完后需等次日重置
- 检查 APPID/APIKey/APISecret 是否匹配

**Q: 讯飞返回 `code: 401 鉴权失败`**

- 优先使用 `x-api-key` 鉴权（代码已默认），确保 APIKey = APIPassword
- 如果 x-api-key 失败，代码会自动回退到 HMAC-SHA256 签名方式

**Q: 百度返回 `err_no: 500`**

- 检查是否已在语音技术控制台领取免费额度
- `access_token` 有效期 30 天，工具已自动管理 token 缓存

**Q: 火山引擎返回鉴权错误**

- 确认已开通后付费或购买资源包
- 检查 `access_token` 不是 `app_id`

### 合成问题

**Q: 合成后音频无声/只有杂音**

- 检查文本是否为空或只有标点
- 尝试换一个发音人（如 xiaoqian → xiaoyan）
- 确认音频播放器支持 MP3 格式

**Q: 文本太长导致超时**

- 讯飞单次 ≤ 2000 汉字，否则分句批量合成
- 火山引擎建议 ≤ 1000 字/次
- 百度 ≤ 500 汉字/次

**Q: WebSocket 连接被断开**

讯飞 WebSocket 有连接超时限制，长文本合成请用批量分句方式。

### 网络问题

**Q: 国内服务器能访问吗？**

- 讯飞: `tts-api.xfyun.cn`
- 百度: `tsn.baidu.com` / `aip.baidubce.com`
- 火山引擎: `openspeech.bytedance.com`

以上均为国内域名，无需科学上网。

**Q: 在 Docker 中部署**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "server.py"]
```

---

## 贡献指南

### 添加新服务商

1. 在 `providers/` 下新建文件，继承 `BaseTTSProvider`
2. 实现 `synthesize()`、`get_available_voices()`、`provider_name`、`estimated_cost_per_char`
3. 在 `providers/__init__.py` 注册到 `PROVIDERS` 字典
4. 在 `config.yaml.example` 添加配置模板

### 本地开发

```bash
git clone https://github.com/aliquanhou/chinese-tts-tool.git
cd chinese-tts-tool
pip install -r requirements.txt
python test_tts.py            # 运行测试
python server.py              # 启动 Web UI
```

### 提交规范

```
feat: 添加新功能
fix: 修复 bug
docs: 文档更新
refactor: 代码重构
```

---

## License

MIT © 2026 — 自由使用、修改、分发。

---

## 致谢

- [讯飞开放平台](https://www.xfyun.cn/) — 提供业界最慷慨的免费额度
- [火山引擎](https://www.volcengine.com/) — 豆包语音大模型驱动的顶级音质
- [百度智能云](https://cloud.baidu.com/) — 企业友好的免费策略
