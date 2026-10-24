# 一书三图 · 百本阅读手帖

[正式阅读](https://shutu.kanglimin.com/) · 100 本书，三幅图与完整阅读笔记。

100 本书按综合阅读榜连续排列，向下滚动即可读完图片、简介与阅读笔记。电脑上每本书的 3:4 封面、三句话、黑板图解并排展示，手机上三图纵向排列。目录可用书名、作者、排名查找并直接跳到书籍位置，支持类别与收藏筛选。手机、电脑和本地 HTM 使用同一套静态文件。

默认采用白色极简主题，也可在页面上方切换黑色极简或原来的纸色主题。白色、黑色主题使用黑白灰与细分隔线，目录、排名说明和图片查看器同步配色。主题选择保存在浏览器，刷新后自动恢复；书籍图片保持原色与完整比例。点击任意图片可以放大细读，页面底部显示当前阅读位置，随时可打开目录。

## 排名与内容

本站编辑编排：长期影响 50%、读者热度 35%、跨地区与跨领域传播 15%。各项以粗档评分，参考豆瓣读者榜、OCLC 馆藏与作者、出版机构资料，不是官方榜单或实时销量排名。详细依据见站内「综合排名依据」及 `content/notebook-ranking-method.json`。排名限定在收录的 100 本中，不代表所有书籍的唯一优劣顺序。

保留原始书目 ID，重新排序后旧收藏与 `#book-ID` 链接继续有效。页面仅展示每本书的三张主图；额外原素材保留在仓库数据与文件中。原书名、作者或内容不一致的情况已在对应书目记录说明。

## 本地使用

双击 `site/index.htm`，保持整个 `site` 文件夹完整；不需要服务器或安装依赖。收藏保存在当前浏览器。在线版可添加到主屏幕，页面和最近浏览的图片可缓存；未访问的图片首次需要联网。

## 修改与生成

`content/books-base.json` 保存书目简介与原导读；`content/notebook-ranking.json` 保存排名、评分与理由；`content/notebook-images.json` 指定封面、三句话、黑板和额外图片。`tools/templates/` 是界面源文件。

```sh
python tools/build_site.py
```

该命令验证 100 个稳定 ID、100 个连续排名及所有图像路径，写入 `site/data/books.json`、`books.js` 和界面文件，生成图像内容指纹及新的 PWA 缓存版本。提交生成后的 `site/`。

新增图卡 SVG、WebP、缩略图及生成工具均保留在仓库。工具所需的 Playwright、Chrome、Python 和 Pillow 需自行配置；可通过 `PLAYWRIGHT_MODULE`、`CHROME_PATH` 和 `PYTHON` 指定运行时。`tools/build_legacy_site.py` 仅作旧版参考，不用于生成当前界面。

需要重新生成补图时，依次运行 `python tools/build_notebook_images.py`、`node tools/render_notebook_images.cjs`，再运行网站构建。图卡工具使用 Windows 的微软雅黑和楷体字体进行尺寸测量与渲染；其他系统须配置对应字体。中间截图和检查报告写入已忽略的 `.notebook-build/`。

修改 `site/assets/icon.svg` 后，用 `node tools/render_icon.cjs` 同步生成192和512像素PNG图标，再构建网站。页面和manifest中的图标地址带内容指纹，固定与指纹资源均预缓存，支持主题升级后的离线展示。

重新生成语义图卡时，依次运行 `python tools/build_notebook_images.py` 与 `node tools/render_notebook_images.cjs`，再运行 `python tools/build_site.py`。前两步默认把截图和逐图字框报告放在已忽略的 `.notebook-build/`；也可通过 `--work-dir` 指定临时目录。图卡源文本固定读取 `content/books-base.json`，按原始 ID 对应，不受综合排名重排影响。当前排字使用 Windows 的微软雅黑和楷体字体文件（`C:/Windows/Fonts/msyh.ttc`、`simkai.ttf`），适用于本机 Windows 生成环境；换平台时需要配置等效字体并重新检查字框。

## 内置生图结果的持久导入

`content/ai-image-overrides.json` 按稳定书目 ID 与图片位置保存已选定的 AI 图片；位置固定为 `cover`、`threeLines`、`blackboard`。空对象不会改变现有图片方案。网站构建先读取 `notebook-images.json`，再覆盖明确指定的位置，因此重建排字图卡或重新运行构建后仍会保留 AI 选择。原图、旧图卡和额外图片不会被删除或改写。

导入工具只接受已标记 `reviewed: true`、可解码、接近 3:4 的 PNG/JPEG，不调用生成接口、不绘图。默认按原始文件 SHA-256 命名并原样复制；发布时使用 `--encode-webp` 保持原尺寸编码为 WebP（quality 92），另生成 420px 缩略图（quality 88），不裁切、重排或改画。原始文件通过 `--originals-dir` 保留原样副本。生成动作使用内置 imagegen；导入工具本身不能鉴定图片来源。

将实际结果写入任意位置的 manifest，例如本地 `work/ai-image-results.json`：

```json
{
  "images": [
    {
      "id": 14,
      "slot": "threeLines",
      "path": "D:/实际生成目录/原始结果.png",
      "title": "原子习惯",
      "prompt": "这张图片实际使用的完整提示词",
      "mode": "built-in-imagegen",
      "reviewed": true
    }
  ]
}
```

也可使用顶层数组；`role` 是 `slot` 的同义字段，两者同时给出时必须一致。相对图片路径以 manifest 所在目录为基准，不依赖默认生图目录。缺少审核标记或 `reviewed: false` 的图片会被拒绝；同一 manifest 不能重复指定同一书目的同一位置。

```sh
python tools/import_ai_images.py --manifest /absolute/path/ai-image-results.json --dry-run
python tools/import_ai_images.py --manifest /absolute/path/ai-image-results.json
python tools/import_ai_images.py --manifest /absolute/path/ai-image-results.json --encode-webp --originals-dir /absolute/path/outputs/AI-originals
python tools/build_site.py
```

可用 `--data-dir`、`--site-dir` 指向其他完整的内容及网站目录。工具先核实全部书目、位置、文件格式、尺寸、内容哈希和目标冲突，再复制文件并更新覆盖表。重新导入相同结果不会重复复制图片或生成记录；导入新结果仅更新对应位置，不删除旧文件。请一次只运行一个导入进程。

完整提示词、审核状态、生成模式及 manifest 的附加元数据保存在 `content/ai-image-provenance.json`。原始文件与网页文件分别记录 SHA-256，方便核查保存和编码。原始绝对路径保留在本地 manifest，提交记录去掉本机路径。Pillow 用于解码与发布编码，不改变构图、文字或语义。完成后检查构建、三张主图和原图保留情况，再按发布流程提交。

## 自动部署

Cloudflare Pages 项目 `shutu-reading-room` 原生连接本仓库。生产分支 `main`，构建命令留空，输出目录 `site`，根目录 `/`。推送 main 后自动部署到 [shutu.kanglimin.com](https://shutu.kanglimin.com/)，不启用预览分支部署。发布结果以该次 GitHub push 对应的部署成功状态和正式网址验收为准。
