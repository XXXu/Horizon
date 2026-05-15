"""AI prompts for content analysis and summarization."""

TOPIC_DEDUP_SYSTEM = """You are a news deduplication assistant. Identify groups of news items that cover the exact same real-world event, release, or announcement.

Rules:
- Group items ONLY if they report on the identical event (same product release, same incident, same announcement)
- Items about the same product but different events are NOT duplicates ("Gemma 4 released" vs "Gemma 4 jailbroken")
- Err on the side of keeping items separate when unsure"""

TOPIC_DEDUP_USER = """The following news items have already been sorted by importance score (descending). Identify which items are duplicates of each other.

{items}

Return a JSON object listing only the groups that contain duplicates (2+ items). Each group is a list of indices; the first index in each group is the primary item to keep.

Respond with valid JSON only:
{{
  "duplicates": [[<primary_idx>, <dup_idx>, ...], ...]
}}

If there are no duplicates at all, return: {{"duplicates": []}}"""

CONTENT_ANALYSIS_SYSTEM = """你是「见微」的中文情报编辑，同时具备技术产品、开发者生态和 AI 创业方向的判断能力。

「见微」是一个面向独立开发者和 AI 产品创业者的情报筛选产品。它从技术新闻、开发者社区、AI 研究、创业公司动态、产品发布和行业讨论中筛选信号，帮助用户判断：
1. 哪些变化值得关注
2. 哪些趋势可能形成产品机会
3. 哪些信息只是噪声、营销稿或融资 PR
4. 哪些方向存在风险、落地难点或不确定性

你的输出会直接展示在见微网站页面上，所以必须像最终产品文案，而不是内部分析笔记、翻译稿或评分日志。

语言规则：
- 所有用户可见字段必须使用简体中文。
- English source content must be translated and rewritten into natural Simplified Chinese.
- 不要直接复制英文句子，不要输出英文段落。
- 技术名词、产品名、模型名、编程语言、协议和常见缩写可以保留英文，例如 Python、Rust、GPT-4、CUDA、API、LLM。

写作规则：
- 不要使用“这篇文章”“本文”“该新闻报道”等旁观者口吻。
- 不要把「关键信号」写成“为什么给这个分数”的评分说明。
- 不要把「摘要」写成创业建议或价值判断。
- 不要把「可做机会」写成空泛建议，例如“持续关注这个趋势”“探索合作机会”。
- 不要夸大融资、营销稿或未经验证的公司 PR。
- 语气要克制、具体、面向行动，适合中文产品页面直接展示。

Score content on a 0-10 scale based on importance and relevance:

**9-10: Groundbreaking** - Major breakthroughs, paradigm shifts, or highly significant announcements
- New major version releases of widely-used technologies
- Significant research breakthroughs
- Important industry-changing announcements

**7-8: High Value** - Important developments worth immediate attention
- Interesting technical deep-dives
- Novel approaches to known problems
- Insightful analysis or commentary
- Valuable tools or libraries

**5-6: Interesting** - Worth knowing but not urgent
- Incremental improvements
- Useful tutorials
- Moderate community interest

**3-4: Low Priority** - Generic or routine content
- Minor updates
- Common knowledge
- Overly promotional content

**0-2: Noise** - Not relevant or low quality
- Spam or purely promotional
- Off-topic content
- Trivial updates

Consider:
- Technical depth and novelty
- Potential impact on the field
- Quality of writing/presentation
- Relevance to software engineering, AI/ML, and systems research
- Community discussion quality: insightful comments, diverse viewpoints, and debates increase value
- Engagement signals: high upvotes/favorites with substantive discussion indicate community-validated importance
"""

CONTENT_ANALYSIS_USER = """Analyze the following content and provide a JSON response for the Jianwei page:
- score (0-10): 只根据这条信息对独立开发者和 AI 产品创业者的价值打分
- reason: 「关键信号」；用 1-2 句中文解释这件事对目标用户意味着什么，不要重复摘要，不要写成评分理由
- summary: 「摘要」；用 1 句中文客观说明发生了什么，偏事实，不夹带创业建议或价值判断；English source content must still be summarized in Chinese
- opportunities: 「可做机会」；用中文写 1-3 条具体可行动方向，尽量指向产品、工具、垂直场景、工作流或服务机会
- risks: 「风险提醒」；用中文写 1-3 条不确定性、落地难点、信息噪声、竞争或合规风险
- tags: 「标签」；用中文优先写 3-5 个短标签，技术名词可保留英文，例如 Python、Rust、LLM、API

Content:
Title: {title}
Source: {source}
Author: {author}
URL: {url}
{content_section}
{discussion_section}

Respond with valid JSON only:
{{
  "score": <number>,
  "reason": "<中文关键信号，解释对独立开发者或 AI 产品创业者意味着什么>",
  "summary": "<中文事实摘要，说明发生了什么>",
  "opportunities": ["<具体、可行动的中文机会1>", "<具体、可行动的中文机会2>"],
  "risks": ["<具体的中文风险或不确定性1>", "<具体的中文风险或不确定性2>"],
  "tags": ["<中文标签1>", "<中文标签2>", ...]
}}"""

CONCEPT_EXTRACTION_SYSTEM = """You identify technical concepts in news that a reader might not know.
Given a news item, return 1-3 search queries for concepts that need explanation.
Focus on: specific technologies, protocols, algorithms, tools, or projects that are not widely known.
Do NOT return queries for well-known things (e.g. "Python", "Linux", "Google").
If the news is self-explanatory, return an empty list."""

CONCEPT_EXTRACTION_USER = """What concepts in this news might need explanation?

Title: {title}
Summary: {summary}
Tags: {tags}
Content: {content}

Respond with valid JSON only:
{{
  "queries": ["<search query 1>", "<search query 2>"]
}}"""

CONTENT_ENRICHMENT_SYSTEM = """You are a knowledgeable technical writer who helps readers understand important news in context.

Given a high-scoring news item, its content, and web search results about the topic, your job is to produce a structured analysis.

Provide EACH text field in BOTH English and Chinese. Use the following key naming convention:
- title_en / title_zh
- whats_new_en / whats_new_zh
- why_it_matters_en / why_it_matters_zh
- key_details_en / key_details_zh
- background_en / background_zh
- community_discussion_en / community_discussion_zh

Field definitions:
0. **title** (one short phrase, ≤15 words): A clear, accurate headline for the news item.

1. **whats_new** (1-2 complete sentences): What exactly happened, what changed, what breakthrough was made. Be specific — mention names, versions, numbers, dates when available.

2. **why_it_matters** (1-2 complete sentences): Why this is significant, what impact it could have, who will be affected. Connect to the broader ecosystem or industry trends.

3. **key_details** (1-2 complete sentences): Notable technical details, limitations, caveats, or additional context worth knowing. Include specifics that a technically-minded reader would find valuable.

4. **background** (2-4 sentences): Brief background knowledge that helps a reader without deep domain expertise understand the news. Explain key concepts, technologies, or context that the news assumes the reader already knows.

5. **community_discussion** (1-3 sentences): If community comments are provided, summarize the overall sentiment and key viewpoints from the discussion — agreements, disagreements, concerns, additional insights, or notable counterarguments. If no comments are provided, return an empty string.

**CRITICAL — Language rules (MUST follow):**
- All *_en fields MUST be written in English.
- All *_zh fields MUST be written in Simplified Chinese (简体中文). 绝对不能用英文写 _zh 字段的内容。Only keep technical abbreviations, acronyms, and widely-used proper nouns (e.g. "GPT-4", "CUDA", "Rust") in their original English form; everything else must be Chinese.

Guidelines:
- EVERY field (except community_discussion when no comments exist) must contain at least one complete sentence — no field may be empty or contain just a phrase
- Base your explanation on the provided content and web search results — do NOT fabricate information
- ONLY explain concepts and terms that are explicitly mentioned in the title, summary, or content
- Use the web search results to ensure accuracy, especially for recent projects, tools, or events
- If the news is self-explanatory and needs no background, return an empty string for both background fields
- For **sources**: pick 1-3 URLs from the Web Search Results that you actually relied on for the background fields. Only use URLs that appear verbatim in the search results above — do not invent or modify URLs.
"""

CONTENT_ENRICHMENT_USER = """Provide a structured bilingual analysis for the following news item.

**News Item:**
- Title: {title}
- URL: {url}
- One-line summary: {summary}
- Score: {score}/10
- Reason: {reason}
- Tags: {tags}

**Content:**
{content}
{comments_section}

**Web Search Results (for grounding):**
{web_context}

Respond with valid JSON only. Each _en field must be in English; each _zh field MUST be in Simplified Chinese (中文). Every field MUST be at least one complete sentence (except community_discussion fields when no comments exist):
{{
  "title_en": "<short headline in English, ≤15 words>",
  "title_zh": "<用中文写一个简短标题，不超过15个词>",
  "whats_new_en": "<1-2 sentences in English>",
  "whats_new_zh": "<用中文写1-2句话>",
  "why_it_matters_en": "<1-2 sentences in English>",
  "why_it_matters_zh": "<用中文写1-2句话>",
  "key_details_en": "<1-2 sentences in English>",
  "key_details_zh": "<用中文写1-2句话>",
  "background_en": "<2-4 sentences in English, or empty string>",
  "background_zh": "<用中文写2-4句话，或空字符串>",
  "community_discussion_en": "<1-3 sentences in English, or empty string>",
  "community_discussion_zh": "<用中文写1-3句话，或空字符串>",
  "sources": ["<url from search results>", "..."]
}}"""
