# Utayomi

**日语歌词处理 Skill**

Utayomi 适合处理用户已经提供的歌词文本或歌词 HTML。它会清理网页复制带来的标签和噪音，添加注音，逐行翻译，并默认生成可以直接打开的 HTML 歌词页。

粘贴歌词时只在本地处理。你明确要求按歌名或歌手找歌词时，Utayomi 可通过可选的 `furigana-lyrics` CLI 搜索；候选有歧义时会先让你选择。

## 你可以怎么用

直接告诉 Agent：

```text
请处理下面这段日语歌词，保留换行，添加平假名并翻译：

夢ならばどれほどよかったでしょう
```

如果粘贴的是网页内容，也可以直接处理：

```text
请清理下面的歌词 HTML，完成注音、翻译并生成 HTML：
<article>
  <h1>星空</h1>
  <p>歌手：示例歌手</p>
  <p>静かな夜に<br>星を見上げる</p>
</article>
```

默认生成 HTML。处理完成后，你还可以继续说：

- “改成罗马音”；
- “不要翻译”；
- “导出 Markdown”。

翻译语言根据你的指令语言、对话语境或明确要求决定，不固定为中文或英文。

## 默认会做什么

- 粘贴歌词时只处理你提供的文本，不访问歌词网站；明确要求搜索时才调用可选的 `furigana-lyrics` CLI；
- 清理 HTML、脚本、菜单和广告等网页噪音；
- 保留歌词换行、重复副歌、括号、和声标记和有意义的短句；
- 默认使用平假名注音并自动翻译；
- 检查原文是否保留、Ruby 是否完整、歌词行和译文行是否对应；
- 生成一个可以直接打开的独立 HTML 文件。

清洗、注音、翻译和 HTML 生成在一次内存流程中完成，不产生 TXT 或中间 Markdown 文件。

## 命令行用法

CLI 只负责确定性的清洗和注音，不调用大模型翻译。

```bash
# 默认输出 HTML
printf '%s\n' '夢ならばどれほどよかったでしょう' | \
  .venv/bin/python scripts/utayomi.py

# 文件输入：在原文件同目录生成带时间戳的新 HTML
.venv/bin/python scripts/utayomi.py --file lyrics.txt

# 明确要求 Markdown 或罗马音
.venv/bin/python scripts/utayomi.py --markdown < lyrics.txt
.venv/bin/python scripts/utayomi.py --romaji < lyrics.txt
```

文件输入不会覆盖原文件，例如：

```text
lyrics.20260807-153012.html
```

CLI 不提供任意输出路径、覆盖开关、引擎选择或中间文件选项。

## 安装

需要 Python 3.10+；安装依赖时需要可用的 Python 包源或本地缓存。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e /path/to/japanese-language-core

# 安装为 Agent Skill，并同时复制统一运行入口
.venv/bin/python scripts/install_utayomi_skill.py
```

共享核心负责通用日语读音和翻译结构校验；可选的 `furigana-lyrics` CLI 负责搜索与获取；Utayomi 负责 Agent 侧确认、歌词处理和页面输出。Utayomi 不内置搜索 CLI。

要使用歌名搜索，请在 Agent 使用的 Python 环境中安装匹配的 Core 与 `furigana-lyrics` CLI wheel。CLI 单独分发，不安装 CLI 时仍可处理你粘贴的歌词：

```bash
python3 -m pip install ./japanese_language_core-*.whl ./furigana_lyrics-*.whl
```

搜索需要网络连接；即使不安装 CLI，粘贴歌词仍可正常处理。

## 不做什么

- 不会自动搜索；按歌名/歌手明确请求时通过可选 CLI 搜索，并在候选有歧义时先让你选择；
- 不生成 Anki 卡片、挖句数据或多套特殊布局；
- 不生成 PNG 或其他预览图片；
- 不把模型翻译伪装成词典释义；
- 不处理普通日语学习文本；
- 不上传用户歌词。

## 开发与测试

```bash
python3 scripts/run_tests.py
```

这个入口会优先使用当前 Python；如果当前环境缺少读音依赖，会自动寻找项目 `.venv`。

测试覆盖歌词清洗、上下文注音、Ruby 生成、HTML 输出、罗马音、时间戳文件输出和共享核心边界。

## 项目结构

```text
SKILL.md                 # Agent 使用的 Skill 说明
PROMPT.md                # 没有 Skill 框架时使用的提示词
scripts/utayomi.py       # 统一入口
scripts/prepare_lyrics.py  # 内部清洗函数
scripts/utayomi_core.py  # 内部读音适配
scripts/build_html.py    # 内部 HTML 渲染器
scripts/install_utayomi_skill.py # 安装 Skill 和运行脚本
tests/                   # 本地回归测试
```

MIT License
