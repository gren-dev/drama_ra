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

## 接真实数据源（必做的一步）

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
