# 一书三图 · 翻页阅读本

[正式阅读](https://shutu.kanglimin.com/) · 100 本书，三页读懂一本。

大幅 3:4 封面，向左滑动依次阅读三句话、黑板图解。目录按综合阅读榜排列，可用书名、作者、排名查找，支持类别与收藏筛选。简介、阅读笔记、排名理由和其他原图默认收起。手机、电脑和本地 HTM 使用同一套静态文件。

## 排名与内容

本站编辑编排：长期影响 50%、读者热度 35%、跨地区与跨领域传播 15%。各项以粗档评分，参考豆瓣读者榜、OCLC 馆藏与作者、出版机构资料，不是官方榜单或实时销量排名。详细依据见站内「综合排名依据」及 `content/notebook-ranking-method.json`。排名限定在收录的 100 本中，不代表所有书籍的唯一优劣顺序。

保留原始书目 ID，重新排序后旧收藏与 `#book-ID` 链接继续有效。原本的独立图卡保留在展开详情中。简介和新增图卡为整理补写，非原书引语。三处原书名、作者或内容不一致的情况已在对应书目记录说明。

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

重新生成语义图卡时，依次运行 `python tools/build_notebook_images.py` 与 `node tools/render_notebook_images.cjs`，再运行 `python tools/build_site.py`。前两步默认把截图和逐图字框报告放在已忽略的 `.notebook-build/`；也可通过 `--work-dir` 指定临时目录。图卡源文本固定读取 `content/books-base.json`，按原始 ID 对应，不受综合排名重排影响。当前排字使用 Windows 的微软雅黑和楷体字体文件（`C:/Windows/Fonts/msyh.ttc`、`simkai.ttf`），适用于本机 Windows 生成环境；换平台时需要配置等效字体并重新检查字框。

## 自动部署

Cloudflare Pages 项目 `shutu-reading-room` 原生连接本仓库。生产分支 `main`，构建命令留空，输出目录 `site`，根目录 `/`。推送 main 后自动部署到 [shutu.kanglimin.com](https://shutu.kanglimin.com/)，不启用预览分支部署。发布结果以该次 GitHub push 对应的部署成功状态和正式网址验收为准。
