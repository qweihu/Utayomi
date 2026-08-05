---
name: utayomi
description: 日语歌词注音与中译对照工具。输入日语歌词文本，输出带 HTML 振假名标注的注音版本和逐句中文翻译，支持平假名与罗马音模式；翻译复用共享的 japanese-translation 能力。
---

# Utayomi

## 核心功能

将日语歌词中的汉字标注读音，支持：
- **平假名模式**：汉字标注平假名（如 `<ruby>夢<rt>ゆめ</rt></ruby>`）
- **罗马音模式**：所有日文字符标注罗马音（如 `<ruby>夢<rt>yume</rt></ruby>`）

注音脚本默认使用公开的 `japanese-language-core` 共享核心（Nihongo Core）的 reading 能力；它包含 Sudachi 上下文读音和 PyKakasi 回退。使用 `--engine legacy` 才会强制旧版 Fugashi/PyKakasi 路径。两个应用共享语言核心；翻译契约由同一核心的 translation 能力与共享技能 `$japanese-translation` 提供，歌词清洗、标题识别和排版仍由 Utayomi 自己负责。

## 运行时选择

不要直接使用裸的 `python` 或 `python3` 运行注音脚本：它们可能没有安装共享引擎及其词典依赖。
运行前先查找当前工作区的 `.venv/bin/python`；如果工作区就是 Bunomi，则优先使用：

```bash
PYTHONPATH=/path/to/japanese-language-core/src /path/to/python \
  /path/to/utayomi/scripts/utayomi_core.py --engine shared
```

如果共享引擎已经安装到当前 Python 环境，则可以省略 `PYTHONPATH`。生产或 Agent 工作流必须使用
`--engine shared`；只有在明确接受兼容模式、且旧版 `fugashi`、`unidic-lite` 和 `pykakasi` 都可导入时，
才使用 `--engine legacy`。`--engine auto` 发生回退时 CLI 会向 stderr 输出警告；不要把回退结果当成共享引擎结果。

## 输入处理

本 Skill 只处理用户主动粘贴或上传的整段文本，不访问、不搜索、不抓取任何外部网页。
输入可以是纯文本，也可以是混杂 HTML 标签的文本。HTML 只作为需要清洗的输入格式，
不是数据来源。

处理顺序：

1. 将用户提供的完整文本视为唯一输入来源，不根据歌名、歌手或链接补抓歌词。
2. 预处理器默认结合输入结构判断标题：如果前两行都很短、第二行像歌手/组合名称，且第三行开始
   出现连续的歌词内容，就将它们识别为歌曲名和歌手；如果开头更像歌词正文，则保留前两行。
   如果用户明确遵循推荐格式——**第 1 行歌曲名，第 2 行歌手名，第 3 行开始为歌词**——可以使用
   `--header-lines 2` 强制保护前两行。
3. 优先运行本地预处理脚本，移除 HTML 标签、`script`/`style` 等非正文内容，解码 HTML 实体，
   并尝试从带有“歌曲名/歌手”等明确标签的内容中提取元信息：
   ```bash
   # 默认进行结构化判断
   cat pasted-text.txt | .venv/bin/python scripts/prepare_lyrics.py --json
   # 已明确确认前两行是歌名、歌手时，可改用：
   cat pasted-text.txt | .venv/bin/python scripts/prepare_lyrics.py --json --header-lines 2
   ```
4. 对清洗后的内容再做一次语义整理，删除明显的菜单、按钮、广告和页面说明，但不要删除重复句、
   副歌、括号内容、和声标记、短句或原始换行结构。
5. 仅将整理出的歌词正文传给注音脚本：
   ```bash
   cat cleaned-lyrics.txt | PYTHONPATH=/path/to/japanese-language-core/src /path/to/python \
     /path/to/utayomi/scripts/utayomi_core.py --engine shared
   ```

如果本地预处理脚本不可用，也必须在 Agent 内完成同样的本地清洗步骤；不得改用网络工具。

歌曲名和歌手名应从整段输入中寻找，而不是只检查第一行。优先依据明确标签、标题或 heading；
如果证据不足，不要臆造名称，应使用“未命名歌曲 / 未知歌手”并在对话中说明信息缺失。

## 输出格式

- **首行加粗规则**：如果输出文本的首行包含歌曲名称和歌手名，**必须将整个首行加粗**（例如：`**歌曲: {歌名} / {歌手名}**`）。
- **正文精简规则**：生成出来的 Markdown 正文**不要显示**“处理结果”“数据来源”“注音方式”“翻译语言”“保存路径”等摘要区块；这些信息只用于对话回复或内部过程判断，不进入文件正文。

### 头部信息（固定格式）
```
**歌曲: {歌名} / {歌手名}**
```

### 歌词排版
- 一行日文歌词，紧跟一行中文翻译
- 每组之间空一行
- 日文歌词中的汉字必须全部标注 `<ruby>`

示例：
```
<ruby>夢<rt>ゆめ</rt></ruby>ならばどれほどよかったでしょう
如果这是梦，那该有多好啊

<ruby>未<rt>いま</rt></ruby>だにあなたのことを<ruby>夢<rt>ゆめ</rt></ruby>にみる
至今仍会在梦中见到你
```

## 质检规则

输出前必须检查：
- [ ] 所有日文汉字都有 `<ruby>` 标注
- [ ] 标题行（如有）已标注
- [ ] 每句日文下方都有对应中文翻译
- [ ] 翻译与日文逐句对应，无整句漏译（专名/引用保留原文可接受）
- [ ] 没有输入文本中的噪音（广告、按钮文字、菜单和页面说明等）

## 禁止事项

- 不要生成歌曲赏析、情感解读
- 不要在生成的歌词 Markdown 正文中使用 emoji 装饰
- 不要添加"质检确认"等自检说明
- 不要在生成的歌词 Markdown 正文中输出“处理结果”或其明细字段
- 不要输出中间过程，只输出最终结果

## 执行步骤

1. **整理输入**：只使用用户粘贴的整段文本；先清洗 HTML 和结构噪音，再识别歌曲名、歌手名和歌词正文
2. **调用注音**：使用上面的共享引擎运行命令，并按需追加 `--romaji`；如果共享引擎确实不可用，才使用 `--engine legacy`
3. **逐句翻译**：使用共享翻译能力 `$japanese-translation`（读取其 `references/zh-CN.md` 约定），将注音后的日文逐句翻译成简体中文，并用其校验脚本确认行数一一对应
4. **排版输出**：按固定格式生成加粗标题（如有）+ 中日对照歌词；不要在 Markdown 正文中附带处理结果摘要
5. **确认保存路径**：只有用户明确要求保存文件时，才向用户确认完整绝对路径；不得自动推导目录、使用当前目录或用时间戳绕过确认。
6. **安全保存**：将最终 Markdown 通过 `scripts/save_markdown.py --output /absolute/path.md` 保存；只有用户明确允许时才追加 `--create-parent` 或 `--overwrite`。
7. **主动告知用户**：文件保存成功后，**务必在对话中主动回复用户**："处理完成！歌词已保存在：【文件的完整绝对路径】"
8. **最终质检**：确认无漏标后输出，并确认正文没有残留 HTML 标签或页面噪音
