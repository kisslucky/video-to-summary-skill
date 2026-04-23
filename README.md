# Video to Summary

把视频页面、媒体文件或字幕内容，统一整理成可交付的文字稿和摘要。

这次整改的重点不是“再堆一个下载脚本”，而是把 `video-to-summary` 改成一个真正能和 `web-access`、CDP、交互式页面处理协同工作的 Skill。

## 现在的定位

- 直链能下：直接走本地处理
- 需要 Cookie / referer：走增强下载
- 需要浏览器点击、展开字幕、滚动、登录：先走 `web-access` / CDP，再把拿到的媒体或字幕喂回本 Skill
- 浏览器/CDP 自身坏了：转 `browser-troubleshooting`

## 支持的三种入口

1. 视频 URL

```bash
python processor.py "<video-url>"
```

2. 浏览器/CDP 导出的媒体文件

```bash
python processor.py --media-file "C:/path/to/audio.m4a" --page-url "<page-url>" --title "<title>"
```

3. 页面已提取到字幕或文字稿

```bash
python processor.py --transcript-file "C:/path/to/captions.txt" --page-url "<page-url>" --title "<title>"
```

## 典型配合方式

### 普通公开视频

- 直接运行 `processor.py`

### YouTube / 需要登录的页面

- 优先试 `--cookies-from-browser chrome`
- 如果还是被挡，转 `web-access` / CDP

### 抖音 / 快手 / 小红书式交互页面

- 先用 `web-access` 在浏览器里打开页面
- 通过点击、滚动、展开字幕或提取媒体地址拿到内容
- 再回到 `processor.py`

## 输出结果

每次运行都会生成一个独立任务目录，里面包含：

- `transcript.txt`
- `summary.md`
- `result.json`
- `audio.m4a`
- 可选的原始媒体文件

## 当前状态

- 已按 `skill-creator` 标准收敛为有效 Skill
- 已加入 Hermes 适配说明
- 已支持和 `web-access` / CDP 的协同入口
- 仍建议后续把 `backend-api.py` 之类 demo/service 逻辑进一步拆出去

## Hermes 适配

适用于 Hermes，前提是 Hermes 会话具备终端和网页访问能力。

- `web-access` 的等价能力：浏览器工具、`web_search`、`web_extract`
- 直链处理：直接运行 `${HERMES_SKILL_DIR}/processor.py`
- 交互式页面：先在浏览器工具里拿字幕、媒体或标题，再交给本 Skill

## License

MIT
