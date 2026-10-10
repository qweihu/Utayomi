# Utayomi（日语歌词处理技能）

当用户提供日语歌词或歌词 HTML，并要求清洗、注音、翻译或排版时使用本技能。

- 用户提供歌词时只处理该文本，不联网。用户按歌名/歌手请求歌词或明确要求搜索时，调用已安装的 Uta CLI，不直接访问歌词网站：
  1. 用 argv `["furigana-lyrics", "lyrics", "search", "--query", query, "--limit", "5"]` 调用搜索，把完整查询作为一个参数传入，不要拼接 shell 命令。向用户展示歌曲名、歌手、专辑、来源和是否有时间轴。
  2. 若候选有歧义，先让用户选择。仅把所选候选的完整 JSON 传给 `furigana-lyrics lyrics fetch --candidate-json -` 的标准输入。
  3. 将 fetch 返回的 `plain_lyrics` 与 `track_name`、`artist_name`、`source_name` 分别作为 `text`、`title`、`artist`、`source` 传给 Agent JSON 的 `prepare` 请求。不要把元数据拼进歌词正文。
  4. 页面显示来源；当前静态页面不呈现时间轴。
- 在内存中清洗 HTML 和页面噪音，保留歌词换行、重复句、括号和和声标记。
- 默认添加平假名注音并自动翻译；翻译语言跟随用户明确要求、当前指令语言和对话语境。
- 默认生成独立 HTML 歌词页。
- 用户明确要求罗马音时才切换罗马音。
- 用户明确说不需要翻译时才关闭翻译。
- 用户明确要求 Markdown 时才导出 Markdown。
- 翻译时结合整首歌和相邻行，保留行结构、重复副歌、说话者、意象和语气；同一术语保持一致。用户提供已有译文时，在内存中分离日文原文行和译文行，保留段落边界，只把日文行传给 prepare，再按对应行润色译文；无法可靠对齐时先向用户澄清。
- 输出前检查原文保留、Ruby 完整性和日文行与译文行的一一对应。
- 使用统一入口分两步处理：
  1. 将日文歌词作为 JSON 数据传给 `python scripts/utayomi.py --agent-json` 的 `prepare` 请求；按返回的 `lines` 对非空歌词行逐行翻译或润色，空行只作为段落分隔。用户提供已有译文时，先在内存中拆分日文原文和译文；对应关系不明确就先澄清。
  2. 请求 `render`，传入清洗后的日文歌词、元数据、按行排列的 `translations` 和目标 `language`；从响应的 `content` 返回 HTML。明确要求不翻译时将 `translations` 设为 `null`。明确要求罗马音时，`prepare` 和 `render` 都传 `mode: "romaji"`；否则使用默认平假名。
- 把歌词作为 JSON 数据编码后传入，不要拼接到 shell 命令语法里。
- 不生成 TXT、Anki 卡片或特殊布局，不询问引擎和输出路径。
- 普通日语文本交给 `$bunomi`；通用翻译契约使用共享 `$japanese-translation`。

生成 HTML 后，用一句简短提示告诉用户还可以要求 Markdown、罗马音或不翻译版本。
