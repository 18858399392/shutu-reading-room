# 一书三图 · 私人阅读室

正式网站：[shutu.kanglimin.com](https://shutu.kanglimin.com/)

100本书，每本包含作者、原创简介和三张主图。提供七类筛选、全文关键词检索、浏览器收藏和大图细读。适配手机和电脑，可添加到主屏幕。

## 部署

Cloudflare Pages 连接本仓库，生产分支 `main`，构建命令留空，输出目录 `site`。推送 main 后由 Cloudflare 自动发布；没有生产分支以外的预览部署。正式自定义域名为 `shutu.kanglimin.com`。

## 本地使用

直接打开 `site/index.htm`，保持整个 site 目录完整；无需安装依赖。也可在该目录用任意静态服务器预览。

## 内容与素材

- `site/` 是经过验收的完整静态网站。
- `content/` 保留100本书的原创简介与导读数据、素材尺寸和SHA-256清单；不含本机私有路径或下载的电子书。
- `tools/build_site.py` 生成书目HTML、数据与导读SVG；需要 Python 和 Pillow。
- `tools/render_supplements.cjs` 通过浏览器渲染SVG，再由Pillow编码成全尺寸WebP和缩略图；需要 Playwright 与 Chrome/Chromium。

原190张PNG保留在原文件夹，站点使用原尺寸WebP。按哈希去掉三张重复图的展示，独立多图保留在详情。新增126张导读卡带“原创补充”标签；简介和导读均非书中引语。书目疑点、选择的明确版本及原图对照记录在对应条目中。选书覆盖长期热门经典和通俗读物，不声称实时销量排名。

修改HTML/CSS/JS及图片后提交即可自动部署。修改content源数据时，应先生成并提交site产物：

```sh
python -m pip install Pillow
python tools/build_site.py --data-dir content --out-dir site
# 安装 Playwright 后，渲染新增或修改过的导读卡：
node tools/render_supplements.cjs
```

可通过 `PLAYWRIGHT_MODULE` 指定已安装的Playwright模块，`CHROME_PATH` 指定Chrome，`PYTHON` 指定Python。

收藏只存于当前浏览器。在线版缓存页面及最近浏览的图片，首次打开图片需要网络。本地版无需联网。图像资源带内容指纹，更新后使用新的缓存地址。
