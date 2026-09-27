# 观察清单

| id | subject | value | 域名 | 摘要级 | fetch | quote |
|----|---------|-------|------|--------|-------|-------|
| o-1 | jev-ecosystem-paper|snapshot_size | 作者报告2170项目/2026-09-22 | arxiv.org |  | f-4 | 2,170 publicly available Jev projects collected from GitHub as of September 22, 2026. |
| o-2 | jev-ecosystem-paper|attention_proxy | 仓库星数不等于未满足需求 | arxiv.org |  | f-4 | these results indicate uneven visibility rather than unmet demand. |
| o-3 | jev-ecosystem-paper|verification_method | 模型初筛及第二模型复核 | arxiv.org |  | f-4 | Each candidate repository is inspected by a GPT-6 Luna Max agent. |
| o-4 | jev-ecosystem-paper|composed_purposes | 作者报告69.7%使用多个决策目的 | arxiv.org |  | f-4 | 69.7% use Jev for two or more purposes |
| o-5 | jev-system|control_owner | 应用代码负责控制流程及执行 | typesafe.ai |  | f-7 | Keep control flow, deterministic rules, and side effects in code. |
| o-6 | jev-system|state_independence | 同一state问题独立判断 | typesafe.ai |  | f-8 | All questions see the same state and are evaluated independently. |
| o-7 | jev-system|fan_out | 支持一次请求并行多个判断 | typesafe.ai |  | f-10 | All questions are evaluated in parallel, so adding more questions usually has little effect on response time. |
| o-8 | jev-1.13|generation | 不适合生成内容 | typesafe.ai |  | f-9 | `jev-1.13` is not trained to generate text. |
| o-9 | jev-1.13|numeric_limits | 算术应由代码执行 | typesafe.ai |  | f-9 | Jev is not a calculator. We strongly recommend implementing any mathematical logic in code. |
| o-10 | jev-1.13|semantic_failure | 结构正确不能保证语义正确 | typesafe.ai |  | f-9 | When the `instructions` and the `criteria` ask for different things, `jev-1.13` might get confused. |
| o-11 | jev-1.13|semantic_failure | 结构正确不能保证语义正确 | arxiv.org |  | f-6 | By construction, every output conforms to the required schema. Yet this guarantee does not tell us whether the model int |
| o-12 | jev-system|input_modality | 只接受文本或文本JSON | typesafe.ai |  | f-8 | Images, audio, and video are not supported (yet). |
| o-13 | jev-system|language_limit | CJK支持但准确率较低 | typesafe.ai |  | f-8 | Jev's primary training language is English; other languages, including CJK scripts, are accepted but currently have lowe |
| o-14 | jev-system|confidence_statistic | 置信度由输出概率分布计算 | typesafe.ai |  | f-12 | `confidence` is a statistic computed from the probability distribution the answer already gives you. |
| o-16 | devagrawal09/jev-review|stars_observed | 618 | github.com |  | f-111 | "stargazerCount":618 |
| o-17 | devagrawal09/jev-review|author_description | 代码差异或代码库审查：分阶段判断风险、选择证据、判断问题机制和严重程度，汇总到本地仪表盘。 | github.com |  | f-111 | This is an experiment in composing fast typed judgments into a review workflow. |
| o-18 | thruwire/foreman|stars_observed | 571 | github.com |  | f-108 | "stargazerCount":571 |
| o-19 | thruwire/foreman|author_description | 在编码 Agent 运行期间，以独立观察循环判断是否偏离任务、卡住、需要验证或已完成，代码决定继续/引导/停止。 | github.com |  | f-108 | Jev assessment accuracy is unproven for this use case and the semantic scores need calibration. |
| o-20 | superagents-lab/jev-search|stars_observed | 467 | github.com |  | f-109 | "stargazerCount":467 |
| o-21 | superagents-lab/jev-search|author_description | 从自然语言判断搜索来源、查询词和时间范围，通过Search1API并行检索，再相关性排序、合并链接、流式显示。 | github.com |  | f-109 | Relevance percentages are model judgments, not verified accuracy. |
| o-22 | gargpratyush/jev-router|stars_observed | 429 | github.com |  | f-107 | "stargazerCount":429 |
| o-23 | gargpratyush/jev-router|author_description | 每次新用户回合用Jev选择Claude Code/Codex的模型档位；回合内部工具循环保持该档位。 | github.com |  | f-107 | Automatic per-turn model routing for Claude Code and OpenAI Codex. |
| o-24 | droidrun/mobile-jev|stars_observed | 404 | github.com |  | f-110 | "stargazerCount":404 |
| o-25 | droidrun/mobile-jev|author_description | 将Android控件和已安装应用变成候选，一次判断操作和目标，通过Mobilerun执行；附实时设备界面、轨迹和任务验证 | github.com |  | f-110 | A completed booking is not demonstrated. |
| o-26 | lakeday-org/perch|stars_observed | 185 | github.com |  | f-112 | "stargazerCount":185 |
| o-27 | lakeday-org/perch|author_description | 语义代码lint：以自然语言规则约束方法/文件，展示问题排序，支持修复后的检查及CI门禁。 | github.com |  | f-112 | Semantic code linting with Jev. |
| o-28 | uehaj/jev-semgrep|stars_observed | 144 | github.com |  | f-113 | "stargazerCount":144 |
| o-29 | uehaj/jev-semgrep|author_description | 逐行按语义筛选文件，支持AND/OR/NOT、跨语言查询和本地正则预筛；README已使用sys1grep名称。 | github.com |  | f-113 | The flip side is that every query pays for the whole corpus again |
| o-30 | sdras/jev-webmcp-extension|stars_observed | 117 | github.com |  | f-114 | "stargazerCount":117 |
| o-31 | sdras/jev-webmcp-extension|auto_readonly | 高置信只读工具允许边输入自动执行 | githubusercontent.com |  | f-141 | if (hints.readOnlyHint && live && call.confidence >= thresholds.auto) return "auto"; |
| o-32 | sdras/jev-webmcp-extension|schema_questions | 工具schema转成并行候选问题 | githubusercontent.com |  | f-142 | Every question rides in one request; Jev answers them in parallel. |
| o-33 | downloads-folder-sorter|author_demonstration | 下载文件按内容归档并重命名 | x.com |  | f-117 | Jev unlocks SO many awesome new ideas.

I built a macOS app that monitors my Downloads folder along with a customisable  |
| o-34 | downloads-folder-sorter|x_likes_2026_09_26 | 1.1K | x.com |  | f-117 | 1.1K |
| o-35 | 500-emails-3-cents|author_demonstration | 批量邮件分类 | x.com |  | f-115 | is very cool. It classified 500 emails in seconds. And it costed 3.5 cents. |
| o-36 | 500-emails-3-cents|x_likes_2026_09_26 | 3.8K | x.com |  | f-115 | 3.8K |
| o-37 | competitor-ad-teardown|author_demonstration | 拆解竞品广告和落地页不一致 | x.com |  | f-118 | jev is INSANE.

in 40 seconds it broke down 724 live ads from 37 brands.

every hook. every format. offer. cta. awarenes |
| o-38 | competitor-ad-teardown|x_likes_2026_09_26 | 6.8K | x.com |  | f-118 | 6.8K |
| o-39 | browser-use-flights|x_likes_2026_09_26 | 9K | x.com |  | f-119 | 9K |
| o-40 | x-post-firewall|author_demonstration | 按自然语言规则过滤社交帖子 | x.com |  | f-116 | I built a browser extension with Jev |
| o-41 | x-post-firewall|x_likes_2026_09_26 | 1.1K | x.com |  | f-116 | 1.1K |
| o-42 | youtube-sponsor-skipper|author_demonstration | 识别并跳过YouTube赞助片段 | x.com |  | f-193 | Just trying out Jev, I made a Chrome extension that:

- Listens to your YouTube audio (optional)
- Detects if it gets to |
| o-43 | youtube-sponsor-skipper|x_likes_2026_09_26 | 1K | x.com |  | f-193 | 1K |
| o-44 | zillow-listing-search|x_likes_2026_09_26 | 958 | x.com |  | f-122 | 958 |
| o-45 | drape-virtual-try-on|author_demonstration | 对话驱动换装选择 | x.com |  | f-121 | jev is insane 🫣

it makes realtime virtual try-on hauls possible.
built this experiment for Drape with |
| o-46 | drape-virtual-try-on|x_likes_2026_09_26 | 4.3K | x.com |  | f-121 | 4.3K |
| o-47 | minecraft-ender-dragon|author_demonstration | 游戏规划器与快速动作选择协作 | x.com |  | f-124 | Readers added context they thought people might want to know |
| o-48 | minecraft-ender-dragon|x_likes_2026_09_26 | 7.9K | x.com |  | f-124 | 7.9K |
| o-49 | lead-outreach-scoring|author_demonstration | 筛出潜客与外联文案的不匹配 | x.com |  | f-127 | JEV is INSANE.

We gave it 700 high-intent leads and personalised outreach messages.

In 40 seconds, it predicted how ea |
| o-50 | lead-outreach-scoring|x_likes_2026_09_26 | 3.4K | x.com |  | f-127 | 3.4K |
| o-51 | sales-copilot|x_likes_2026_09_26 | 198 | x.com |  | f-123 | 198 |
| o-52 | jev-plays-mario|x_likes_2026_09_26 | 2.9K | x.com |  | f-125 | 2.9K |
| o-53 | 1kpapers|author_demonstration | 给论文库批量分配主题 | x.com |  | f-192 | I used Jev to classify 1,018 AI research papers.

The result: $0.08 total cost and 256ms median end-to-end latency per p |
| o-54 | 1kpapers|x_likes_2026_09_26 | 1.9K | x.com |  | f-192 | 1.9K |
| o-55 | stagehand-remote-browser|author_demonstration | 远程浏览器的元素/动作选择 | x.com |  | f-129 | we built blazing fast computer/browser use with Jev + |
| o-56 | stagehand-remote-browser|x_likes_2026_09_26 | 773 | x.com |  | f-129 | 773 |
| o-57 | cute-x|x_likes_2026_09_26 | 461 | x.com |  | f-128 | 461 |
| o-58 | internal-link-tool|author_demonstration | 找站内值得相互链接的网页 | x.com |  | f-194 | Jev for classifying and selecting the links.

BYOK or pay $1 to use mine. It works for up to 500 pages and gives you a C |
| o-59 | internal-link-tool|x_likes_2026_09_26 | 280 | x.com |  | f-194 | 280 |
| o-60 | on-device-audio-pipeline|author_demonstration | 把音频按任务路由至不同本地模型 | x.com |  | f-130 | Jev + on-device models = results in seconds with no LLM in the loop.

Quick demo app to show the possibilities. Drop in  |
| o-61 | on-device-audio-pipeline|x_likes_2026_09_26 | 157 | x.com |  | f-130 | 157 |
| o-62 | ghostfeed-reaction-library|author_demonstration | 按反应与镜头结构搜索视频素材 | x.com |  | f-131 | How to generate 1000s of AI UGC reactions to flood your ugc accounts |
| o-63 | ghostfeed-reaction-library|x_likes_2026_09_26 | 110 | x.com |  | f-131 | 110 |
| o-64 | jev-auto-tagging|author_demonstration | 输入时自动选标签 | x.com |  | f-132 | more magical UI with JEV: auto-tagging |
| o-65 | jev-auto-tagging|x_likes_2026_09_26 | 239 | x.com |  | f-132 | 239 |
| o-66 | jevpilot|author_demonstration | 驾驶模拟中的轨迹选择 | x.com |  | f-197 | I rebuilt Tesla Full Self Driving with Jev in less than an hour.

This model is a total unlock. |
| o-67 | jevpilot|x_likes_2026_09_26 | 4.8K | x.com |  | f-197 | 4.8K |
| o-68 | superx-post-scoring|x_likes_2026_09_26 | 1.3K | x.com |  | f-136 | 1.3K |
| o-69 | ai-slop-detector|author_demonstration | 识别网站模板化风格信号 | x.com |  | f-196 | madewithjev.com/free-tools/ai-… |
| o-70 | ai-slop-detector|x_likes_2026_09_26 | 2 | x.com |  | f-196 | 2 |
| o-71 | x-post-analysis|author_demonstration | 给历史帖子分类并分析内容规律 | x.com |  | f-137 | I gave Jev 3,282 of my X posts across 100M views and asked it to find what actually works for growth.

4,252,330 tokens  |
| o-72 | x-post-analysis|x_likes_2026_09_26 | 749 | x.com |  | f-137 | 749 |
| o-73 | live-viral-post-analyzer|author_demonstration | 写草稿时即时显示类别与潜力评分 | x.com |  | f-138 | Just created this with Jev by |
| o-74 | live-viral-post-analyzer|x_likes_2026_09_26 | 924 | x.com |  | f-138 | 924 |
| o-75 | jev-plays-doom|author_demonstration | Doom快速动作选择 | x.com |  | f-139 | We love how this doomo doomonstrates real-time intelligence and what can be doone with code + AI!

~10 calls/sec = ~$7/h |
| o-76 | jev-plays-doom|x_likes_2026_09_26 | 5K | x.com |  | f-139 | 5K |
| o-77 | jev-trader|displayed_stars_2026_09_26 | 2.5k | github.com |  | f-143 | 2.5k |
| o-78 | instant-compaction|source_stated_purpose | 判断哪些工具调用/结果仍相关，裁剪上下文而保留原文 | x.com |  | f-146 | Jev can make it instant by scoring every tool call |
| o-79 | instant-compaction|displayed_likes_2026_09_26 | 10K | x.com |  | f-146 | 10K |
| o-80 | fraud-detection-jev-kimi|source_stated_purpose | 先快速识别诈骗邮件，再把低信心项升级大模型 | x.com |  | f-145 | Jev classified 100 emails in 1.42 seconds |
| o-81 | fraud-detection-jev-kimi|displayed_likes_2026_09_26 | 871 | x.com |  | f-145 | 871 |
| o-82 | postgres-jev-function|source_stated_purpose | SQL中的自然语言筛选、排序、分类 | x.com |  | f-148 | a PostgreSQL extension that searches your whole database in natural language |
| o-83 | postgres-jev-function|displayed_likes_2026_09_26 | 2.8K | x.com |  | f-148 | 2.8K |
| o-84 | computer-use-without-screenshots|source_stated_purpose | 本地视觉分割+OCR转成候选控件，再选点击动作 | x.com |  | f-147 | On-device OCR reads the labels. That text is all Jev gets. |
| o-85 | computer-use-without-screenshots|displayed_likes_2026_09_26 | 2K | x.com |  | f-147 | 2K |
| o-86 | bot-chief-of-staff|source_stated_purpose | 按任务唤醒合适Agent并匹配模型 | x.com |  | f-144 | Jev reads the task, wakes the right teammates off the bench |
| o-87 | bot-chief-of-staff|displayed_likes_2026_09_26 | 184 | x.com |  | f-144 | 184 |
| o-88 | subway-surfers|source_stated_purpose | 跑酷游戏动作选择及并行控制实验 | x.com |  | f-150 | Here is Jev playing subway surfers |
| o-89 | subway-surfers|displayed_likes_2026_09_26 | 4.1K | x.com |  | f-150 | 4.1K |
| o-90 | smash-bros|source_stated_purpose | 对战游戏里同时为多个角色选动作 | x.com |  | f-149 | he is controlling all 4 different characters. |
| o-91 | smash-bros|displayed_likes_2026_09_26 | 3.6K | x.com |  | f-149 | 3.6K |
| o-92 | realtime-ad-blocker|source_stated_purpose | 动态DOM广告候选分类并移除 | x.com |  | f-157 | It checks every dom element and classifies as ad/non-ad and removes it if true |
| o-93 | realtime-ad-blocker|displayed_likes_2026_09_26 | 3.8K | x.com |  | f-157 | 3.8K |
| o-94 | invoice-finder|source_stated_purpose | 跨网站自动找到账单入口、列出发票、记住路径 | x.com |  | f-156 | Remembers where invoices live for next time |
| o-95 | invoice-finder|displayed_likes_2026_09_26 | 44 | x.com |  | f-156 | 44 |
| o-96 | job-match-prediction|source_stated_purpose | 候选人资料与数百公司/岗位匹配并找不匹配点 | x.com |  | f-154 | We gave it 400 companies and one candidate profile. |
| o-97 | job-match-prediction|displayed_likes_2026_09_26 | 1.7K | x.com |  | f-154 | 1.7K |
| o-98 | realtime-game-levels|source_stated_purpose | 游戏关卡结构的实时选择/组合 | x.com |  | f-151 | Jev can generate game levels in real time. |
| o-99 | realtime-game-levels|displayed_likes_2026_09_26 | 2.8K | x.com |  | f-151 | 2.8K |
| o-100 | diffjury|source_stated_purpose | 公共PR变更风险分类、审查深度和专项审查路由 | railway.app |  | f-152 | Jev decides if this PR is risky or not |
| o-101 | is-malicious|source_stated_purpose | 运行代码前扫描仓库中的恶意行为迹象 | github.com |  | f-153 | A codebase scanner that helps you not run malicous code |
| o-102 | is-malicious|displayed_stars_2026_09_26 | 28 | github.com |  | f-153 | 28 |
| o-103 | skillbox|source_stated_purpose | 自托管技能库按任务推荐合适技能 | github.com |  | f-155 | Self-hosted, versioned skills library for AI agents. |
| o-104 | skillbox|displayed_stars_2026_09_26 | 247 | github.com |  | f-155 | 247 |
| o-105 | smart-copy-paste|source_stated_purpose | 根据复制内容与粘贴目标决定适合的粘贴形式 | x.com |  | f-164 | what if copy/paste was smart? |
| o-106 | smart-copy-paste|displayed_likes_2026_09_26 | 9.8K | x.com |  | f-164 | 9.8K |
| o-107 | jev-studio-v020|source_stated_purpose | Jev决策接口封装为CLI/MCP | x.com |  | f-159 | just shipped jev-studio v0.2.0 |
| o-108 | jev-studio-v020|displayed_likes_2026_09_26 | 1 | x.com |  | f-159 | 1 |
| o-109 | stuntd|source_stated_purpose | 学习应用中的结构化判断，以本地模型替代调用 | github.com |  | f-160 | Local proxy that learns your app |
| o-110 | stuntd|displayed_stars_2026_09_26 | 30 | github.com |  | f-160 | 30 |
| o-111 | skill-picker|source_stated_purpose | 按当前任务给本地技能排序并建议调用 | github.com |  | f-158 | Rank your agent skills against a request |
| o-112 | skill-picker|displayed_stars_2026_09_26 | 0 | github.com |  | f-158 | 0 |
| o-113 | meta-ads-landing-teardown|source_stated_purpose | Meta广告及落地页类型/优惠/销售语言的批量拆解 | x.com |  | f-161 | categorizes the type of page, offers |
| o-114 | meta-ads-landing-teardown|displayed_likes_2026_09_26 | 23 | x.com |  | f-161 | 23 |
| o-115 | frevana-ad-research|source_stated_purpose | TikTok品类广告分类、聚类和创意排行榜 | x.com |  | f-163 | Jev made competitor ad research |
| o-116 | frevana-ad-research|displayed_likes_2026_09_26 | 5 | x.com |  | f-163 | 5 |
| o-117 | docjev|source_stated_purpose | 按自然语言规则分类文档并拆分混合PDF资料包 | github.com |  | f-162 | Document classification and splitting with Jev |
| o-118 | docjev|displayed_stars_2026_09_26 | 456 | github.com |  | f-162 | 456 |
| o-119 | designer-jev|source_stated_purpose | 输入语义条件时匹配对象从物品堆里实时浮起 | x.com |  | f-170 | when a designer gets access to Jev |
| o-120 | designer-jev|displayed_likes_2026_09_26 | 10K | x.com |  | f-170 | 10K |
| o-121 | cline-jev-browser|source_stated_purpose | Cline中通过浏览器执行任务 | x.com |  | f-165 | We built a plugin that gives Jev a browser in Cline |
| o-122 | cline-jev-browser|displayed_likes_2026_09_26 | 690 | x.com |  | f-165 | 690 |
| o-123 | webmcp-side-panel-extension|source_stated_purpose | 逐键从页面WebMCP schema预测工具和参数并联动执行 | x.com |  | f-166 | When you type, on every keystroke it picks the relevant page |
| o-124 | webmcp-side-panel-extension|displayed_likes_2026_09_26 | 1.1K | x.com |  | f-166 | 1.1K |
| o-125 | 10k-trading|source_stated_purpose | 模拟或实盘交易决策展示 | x.com |  | f-167 | I gave Jev $10,000 and let it trade |
| o-126 | 10k-trading|displayed_likes_2026_09_26 | 1.6K | x.com |  | f-167 | 1.6K |
| o-127 | x-algorithm-simulator|source_stated_purpose | 发布前模拟帖子受欢迎度和全局动态流 | x.com |  | f-169 | rebuilt the X algorithm with Jev |
| o-128 | x-algorithm-simulator|displayed_likes_2026_09_26 | 1.1K | x.com |  | f-169 | 1.1K |
| o-129 | yc-indexor|source_stated_purpose | 多模态检索YC公司并让匹配logo从物理堆中浮起 | github.com |  | f-168 | Describe a YC startup in any words |
| o-130 | yc-indexor|displayed_stars_2026_09_26 | 50 | github.com |  | f-168 | 50 |
| o-131 | browser-use-flights|execution_limit | search_not_booking | github.com |  | f-195 | It does not select or book a flight. |
| o-132 | minecraft-ender-dragon|control_limit | structured_state_not_screenshots | github.com |  | f-198 | This is structured-state control, not control from screenshots or individual key presses. |
| o-133 | minecraft-ender-dragon|world_limit | peaceful_known_seed | github.com |  | f-198 | The route was surveyed in a separate test world. |
| o-134 | 1kpapers|deployment_limit | classification_still_under_evaluation | x.com |  | f-192 | I’m running evals on the Jev classifications before replacing the current ones |
| o-135 | jevpilot|deployment_limit | driving_simulator | github.com |  | f-135 | A demo project showing Tesla Autopilot-like behavior using |
| o-136 | youtube-sponsor-skipper|execution_limit | can_overshoot_in_listen_mode | github.com |  | f-120 | The last jump in Listen mode can overshoot into content by up to one step. |
| o-137 | browser-use-flights|github_stars_2026_09_26 | 20.4k | github.com |  | f-195 | 20.4k |
| o-138 | youtube-sponsor-skipper|github_stars_2026_09_26 | 103 | github.com |  | f-120 | 103 |
| o-139 | minecraft-ender-dragon|github_stars_2026_09_26 | 553 | github.com |  | f-198 | 553 |
| o-140 | jevpilot|github_stars_2026_09_26 | 186 | github.com |  | f-135 | 186 |
| o-141 | jev-trader|default_mode | mock heuristic | github.com |  | f-143 | is a momentum heuristic stand-in. |
| o-142 | docjev|inference_boundary | hosted Jev even with local OCR | github.com |  | f-162 | Jev is a hosted service; local OCR does not make inference offline. |
| o-143 | realtime-ad-blocker|readme_caveat | demo not production ad blocker | github.com |  | f-203 | This is a fun side project, not a real ad blocker. |
| o-144 | webmcp-side-panel-extension|schema_driven | tool choices derived from page schemas | github.com |  | f-199 | Tool selection is derived from the page |
| o-145 | webmcp-side-panel-extension|execution_boundary | read-only can auto; state change requires Enter | github.com |  | f-199 | Calls that change state require |
| o-146 | instant-compaction|compaction_style | prunes selected tool messages; retained content verbatim | github.com |  | f-202 | This library never rewrites anything. |
| o-147 | typesafe-computer-use|source_title | GitHub - awlevin/typesafe-computer-use: Computer use for abo | github.com |  | f-172 | GitHub - awlevin/typesafe-computer-use: Computer use for about $0.0002 a step: OCR the screen, classify the next action  |
| o-148 | jev-drone|source_title | GitHub - RomanSlack/jev-drone: Camera-only autonomous drone  | github.com |  | f-175 | GitHub - RomanSlack/jev-drone: Camera-only autonomous drone in MuJoCo with a small judgment model (TypeSafe Jev) in the  |
| o-149 | every-editorial-judgments|source_title | Mini-Vibe Check: TypeSafe's Jev Judged Everything I’ve Writt | every.to |  | f-176 | Mini-Vibe Check: TypeSafe's Jev Judged Everything I’ve Written in 0.7 Seconds |
| o-150 | jev-plays-chess|source_title | TypeSafe Jev Played Chess — And Landed Next to Reasoning Mod | dev.to |  | f-177 | TypeSafe Jev Played Chess — And Landed Next to Reasoning Models - DEV Community |
| o-151 | jev-voice-browser|source_title | GitHub - moritzkremb/jev-voice-browser: Control a real brows | github.com |  | f-183 | GitHub - moritzkremb/jev-voice-browser: Control a real browser by voice. Jev (TypeSafe System One) decides intent + targ |
| o-152 | jevlike|source_title | GitHub - vinnylarouge/jevlike · GitHub | github.com |  | f-187 | GitHub - vinnylarouge/jevlike · GitHub |

## 无果搜索（负结果）

- jev-ecosystem-paper|dataset_link: Inspected arXiv HTML body and all hyperlinks; no downloadable full 2170-repository dataset link found. This does not prove no dataset exists elsewhere. (searches: f-4)
