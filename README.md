# 短剧题材雷达 (drama-radar)

采集公开榜单 → LLM 结构化打标 → 聚类发现新题材 → 生成趋势周报 → Streamlit 站点。

## 目录

```
crawler/            采集层
  base.py           Fetcher(重试/限速/UA/快照落盘)、DramaItem、ingest 跨平台去重合并
  sources/          dataeye.py 榜单 · fanqie.py 番茄小说榜 · sample.py 样例源(跑通用)
  run.py            python -m crawler.run [source...]
analysis/           LLM 分析层
  llm.py            提供方抽象：anthropic / openai_compat(DeepSeek,Qwen) / mock
  tagger.py         第一档：小模型全量打标 → genre/sub_genre/hook_type/audience/era/tags
  sentiment.py      评论情感 pos/neg/neu
  cluster.py        第二档：embedding+KMeans 发现词表外的新簇，LLM 命名
  report.py         第三档：强模型只看变化最大的数据，写周报
app/dashboard.py    站点：题材趋势 / 新兴题材 / 剧集库 / AI 周报
db/                 SQLAlchemy 模型 (drama, platform_listing, metric_snapshot, comment, cluster, report)
taxonomy.yaml       题材词表（打标口径在这改）
pipeline.py         一键跑完整流水线
scheduler.py        常驻调度：每 4h 采集+打标，周一早 8 点聚类+周报
```

## 快速开始

```bash
pip install -r requirements.txt
playwright install chromium          # 只有用真实数据源时才需要
cp .env.example .env                 # 填 LLM key；不填走 mock 也能跑通
python pipeline.py                   # 采集(样例) → 打标 → 情感 → 聚类 → 周报
streamlit run app/dashboard.py
```

多跑几次 `python -m crawler.run` 就有趋势曲线了（样例源每次热度带随机波动）。

## 数据源

默认启用两个真实源（`crawler/run.py` 的 `ENABLED`）：

**红果短剧官方网页版 hongguoduanju.com**（`crawler/sources/hongguo.py`）：字节官方 SEO 榜单页，服务端渲染，不用逆向 App。
四个榜：总榜 / 真人剧 / **AI剧** / 漫剧，每榜 5 页 100 条，自带简介、热度、评分、收藏、点赞、标签、新剧标记。
每个榜单单独记 snapshot（platform=`hongguo:AI剧` 等），站点左侧「数据范围」可以只看 AI 剧的题材动量。

**短剧百科 duanjubaike.net**（`crawler/sources/duanjubaike.py`）：聚合番茄/红果/河马/点众等平台的每日热度榜，
抓热播/新剧/热搜/收藏四个榜 + 详情页（简介、标签、出品方、上线日期）。解析只认链接和文字模式，不依赖 class 名。
每次运行最多补抓 60 个详情页（`DETAIL_BUDGET`），首轮之后每天只有新剧需要补。
这个站没有评论，观众反馈那页要等接上抖音/快手评论源才有数据。

## 接其他数据源（可选）

我写代码时访问不了这些站，`dataeye.py` / `fanqie.py` 里的 URL 和 CSS 选择器是占位，要按真实页面校一遍：

1. 浏览器打开榜单页 → F12 → **Network** 面板，过滤 XHR/Fetch，找返回榜单 JSON 的请求。
   有的话把地址填到 `API_URL`，改 `parse_api()` 里的字段路径。这是最稳的路线。
2. 没有 JSON 接口就用 **Elements** 面板找列表容器，改 `ITEM_SEL / TITLE_SEL / HEAT_SEL`。
3. 单独跑 `python -m crawler.run dataeye` 看日志和 `data/snapshots/` 里落盘的原始页面。
4. 通了以后把 `crawler/run.py` 的 `ENABLED` 加上这个源。

加新源：继承 `BaseSource`，`fetch()` 产出 `DramaItem` 即可，去重合并和入库不用管。

## 关于红果

红果没有网页端和公开接口，直接抓 App 需要逆向签名且违反其用户协议，不建议做成公开站点的数据源。
本项目的思路是用榜单站 + 番茄小说榜（红果内容上游）+ 抖音/快手话题 交叉还原红果的题材热度。

## 换模型 / 换 embedding

- 打标用便宜模型（Haiku / deepseek-chat），周报用 `REPORT_MODEL` 指定更强的。
- 聚类默认字符 TF-IDF（零依赖）。要换真 embedding，改 `analysis/cluster.py` 的 `embed()` 返回 `(n, dim)` 矩阵即可。

## 下一步（按优先级）

1. 校准 dataeye / fanqie 选择器，关掉 sample 源
2. 配 LLM key，跑 `python -m analysis.tagger --all` 重打一遍，看 `taxonomy.yaml` 词表要不要调
3. 加抖音/快手评论源（评论比播放量更能说明观众要什么）
4. 数据稳定后把 SQLite 换 Postgres（改 `DATABASE_URL` 即可），Streamlit 换 FastAPI + Next.js

## 部署：Supabase + GitHub Actions + Streamlit Cloud

三边共用一个 Postgres：本地/Actions 写，Streamlit Cloud 读。

### 1. Supabase 建库
1. supabase.com 新建项目，记住数据库密码
2. Project Settings → Database → Connection string → 选 **Session pooler**（IPv4 兼容，Actions 和 Streamlit Cloud 都能连），复制 URI
3. 把 `[YOUR-PASSWORD]` 换成密码，末尾加 `?sslmode=require`，得到 `DATABASE_URL`
4. 本地 `.env` 里 `DATABASE_URL` 改成它，跑 `python pipeline.py`，表会自动建好，Supabase 后台 Table Editor 能看到数据

### 2. 推到 GitHub
`.env` 已在 `.gitignore` 里，确认没被提交。仓库 Settings → Secrets and variables → Actions，添加：
`DATABASE_URL`、`OPENAI_COMPAT_BASE_URL`、`OPENAI_COMPAT_API_KEY`、`OPENAI_COMPAT_MODEL`（可选 `REPORT_MODEL`）。
`.github/workflows/crawl.yml` 会每 6 小时采集打标、周一生成周报；Actions 页面可以手动点 Run workflow 先试一次。

### 3. Streamlit Cloud
share.streamlit.io → New app → 选仓库，Main file 填 `app/dashboard.py`。
Advanced settings → Secrets 粘贴 `.streamlit/secrets.toml.example` 的内容（填真实值）。
以后数据由 Actions 自动更新，站点刷新即可（缓存 5 分钟）。
