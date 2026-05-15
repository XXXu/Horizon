# AGENTS.md instructions for Horizon

## 语言偏好

- 与用户交流时必须使用中文。
- 新增或修改的 Markdown 文档内容优先使用中文。
- README、设计文档、实施计划、提示词文档、说明文档都优先使用中文。
- 除非用户明确要求使用其他语言，否则不要切换到英文。

## 与见微的关系

- Horizon 是独立的数据采集与 AI 分析引擎。
- `jianwei_web` 是独立的网站产品层。
- Horizon 不承载见微的网站页面、订阅入口、数据库模型或部署入口。
- 两者通过见微 artifact JSON 衔接。

## 见微当前产品定位

- 见微当前前台产品定位先收敛为：面向“独立开发者 / AI 产品创业者”的 AI 情报网站。
- 因此 Horizon 当前优先为 `indie-maker` 角色提供真实数据源抓取、AI 打分和 artifact 导出。

## 多角色扩展边界

- 虽然见微前台当前只主推 `indie-maker`，但 Horizon 导出能力必须继续支持多角色。
- 不要把 `horizon-jianwei` 或 `src.integrations.jianwei` 写死为只能导出 `indie-maker`。
- `--persona-slug` 参数必须保留，artifact 中的 `analysis.persona_slug` 必须保留。
- 未来扩展跨境卖家、投资观察者、企业 AI 应用负责人等角色时，应通过不同 persona slug、数据源配置和提示词策略扩展。

## 开发约定

- 优先保持 Horizon 原有 pipeline：抓取、去重、AI 打分、过滤、导出。
- 不要把见微的数据库写入逻辑放进 Horizon。
- 提交前至少运行：

```bash
python -m pytest -q
```
