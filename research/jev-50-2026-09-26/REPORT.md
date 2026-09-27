# Jev：50个社区案例与万界门的组合机会

调研日期：2026-09-26。只做公开资料研究，未修改应用、未运行这些案例、未调用付费推理。

先说最贴近万界门的发现：**让输入不断改变当前任务中的对象、条件、工具和结果之间的关系，才会产生你想要的界面。**下面的案例分别展示了其中一部分；把这些部分连起来，是万界门可以探索的产品方向。

## 这50个案例如何选出

从 [Made with Jev社区榜单](https://madewithjev.com/most-voted) 抽取84个构建条目，逐条打开详情；交叉查阅 [GitHub项目目录](https://jevai.dev/projects/)、项目原仓库、作者原帖和官方文档。剔除模型复现、SDK、教程、汇总帖，合并同一项目的重复演示，再按社区关注度和用途多样性筛成50例。

**这不是可证明的“全网热度前50”。**公开平台没有统一排名；本文以热门案例为主体，也保留少量低热度但与产品探索相关的案例，低热度直接显示。编号按用途编排，不代表名次。X赞数、浏览量与GitHub星数分开展示，不做伪造的综合热度分。目录中的赞助位不作为热度依据。

表内X数据来自本次抓取的作者原帖显示值，GitHub数据来自原仓库页面，均为2026-09-26快照，K/M为平台自身的取整显示。热度是关注线索，不能说明留存、付费或效果。功能栏均归属于作者/仓库的描述；不把作者演示当独立实测。部分极简视频帖的功能说明仅能从收录页获得，逐条标注。

## 50例总览

“可借用的组合”是本文对案例结构的分析，不承诺其中每个环节由Jev独立完成。点击案例名看原始发布，点击热度看计数来源。

### 随输入变化的界面

| 编号 | 案例／原始来源 | 本次热度 | 作者想解决的问题 | 可借用的组合 |
|---|---|---|---|---|
| 01 | [输入时物件浮起](https://x.com/heystefan_/status/2101369117496521042) | [X 10K赞 / 1M浏览](https://x.com/heystefan_/status/2101369117496521042) | 从一堆对象中按模糊含义找东西 | 意图判断＋对象排序＋连续动效 |
| 02 | [智能复制粘贴](https://x.com/marcus_lowe/status/2101476399488160013) | [X 9.8K赞 / 1M浏览](https://x.com/marcus_lowe/status/2101476399488160013) | 相同内容粘到不同地方需要反复整理 | 剪贴板内容＋目标语境＋格式选择 |
| 03 | [Jev × WebMCP](https://x.com/sarah_edo/status/2102025642862600634) | [X 1.1K赞 / 74.7K浏览](https://x.com/sarah_edo/status/2102025642862600634) | 不记网站菜单也能调用合适功能 | 页面工具声明＋逐字参数判断＋自动只读查询 |
| 04 | [预测式启动器](https://x.com/dabit3/status/2100756930054504776) | [X 2.4K赞 / 430.8K浏览](https://x.com/dabit3/status/2100756930054504776) | 记不住文件名，只记得刚下载的PDF | 输入意图＋本地候选＋实时重排 |
| 05 | [预测式电子表格](https://x.com/dabit3/status/2100780008193020049) | [X 1.2K赞 / 276.6K浏览](https://x.com/dabit3/status/2100780008193020049) | 每次给表格加语义分类都要写规则 | 列名含义＋逐行判断＋自动填列 |
| 06 | [输入中自动打标签](https://x.com/designgurra/status/2102726891153338374) | [X 239赞 / 15.6K浏览](https://x.com/designgurra/status/2102726891153338374) | 写完还要手工找标签、选类别 | 文本变化＋多标签判断＋轻量控件 |
| 07 | [X界面实时改样式](https://x.com/hedachi/status/2101952056768770247) | [X 461赞 / 30.8K浏览](https://x.com/hedachi/status/2101952056768770247) | 信息呈现无法随偏好改变 | 页面对象＋判断＋样式规则 |
| 08 | [指向与语音画布](https://x.com/jackcheng/status/2100729670991802386) | [X 4.9K赞 / 1.1M浏览](https://x.com/jackcheng/status/2100729670991802386) | 口头说“把这个去掉”缺少指代对象 | 手势定位＋语音转写＋动作选择 |
| 09 | [自然语言计算笔记](https://x.com/thekitze/status/2100873520951808403) | [X 358赞 / 42.1K浏览](https://x.com/thekitze/status/2100873520951808403) | 数字、单位和普通文字混杂 | 语义识别＋计算器＋单位换算 |
| 10 | [Drape对话试衣](https://x.com/nailthy62/status/2101388186916454439) | [X 4.3K赞 / 555.2K浏览](https://x.com/nailthy62/status/2101388186916454439) | 试衣时反复切菜单、选衣服 | 语音转写＋衣橱候选＋试衣呈现 |

### 搜索、整理与资料

| 编号 | 案例／原始来源 | 本次热度 | 作者想解决的问题 | 可借用的组合 |
|---|---|---|---|---|
| 11 | [下载文件自动归档](https://x.com/marcelpociot/status/2100906882365788167) | [X 1.1K赞 / 139.1K浏览](https://x.com/marcelpociot/status/2100906882365788167) | 下载目录混乱，手工找文件改名字 | 文件事件＋语义分类＋归档规则 |
| 12 | [批量邮件分类](https://x.com/rileybrown/status/2100404532119269426) | [X 3.8K赞 / 296.5K浏览](https://x.com/rileybrown/status/2100404532119269426) | 大量消息需要逐封看后再分流 | 消息内容＋分类规则＋列表分组 |
| 13 | [Zillow隐含条件找房](https://x.com/venturetwins/status/2101341075684434245) | [X 958赞 / 108.6K浏览](https://x.com/venturetwins/status/2101341075684434245) | 固定筛选器不支持建筑风格等要求 | 已有房源＋自然语言条件＋排序 |
| 14 | [1kpapers论文浏览](https://www.1kpapers.com/) | [X 1.9K赞 / 334.5K浏览](https://x.com/nutlope/status/2100426999546184123) | 上千论文无法按主题快速探索 | 其他模型摘要＋Jev主题分类＋浏览视图 |
| 15 | [Ghostfeed反应视频检索](https://x.com/meetshukla_/status/2102272479674642554) | [X 110赞 / 16.7K浏览](https://x.com/meetshukla_/status/2102272479674642554) | 素材多但按文件名找不到情绪和结构 | 视觉模型提取＋语义标签＋素材检索 |
| 16 | [PostgreSQL语义WHERE](https://x.com/iam_zachi/status/2100679300756435135) | [X 2.8K赞 / 480.8K浏览](https://x.com/iam_zachi/status/2100679300756435135) | SQL条件难表达“符合这段描述” | 数据库行＋语义谓词＋缓存 |
| 17 | [DocJev文档拆包](https://github.com/jerryjliu/docjev) | [X 923赞 / 92K浏览](https://x.com/jerryjliu0/status/2102479924032577686) | 混合PDF内多种文档需要分类切开 | OCR＋页面分类＋边界判断 |
| 18 | [YC Indexor公司探索](https://github.com/Aayan-DEV/aayans-yc-indexor) | [X 1.6K赞 / 119.9K浏览](https://x.com/aaayandev/status/2102137061490794730) | 关键词难同时覆盖行业、描述和视觉线索 | 多路召回＋Jev重排＋视觉对象界面 |
| 19 | [keep.md搜索与标签](https://x.com/iannuttall/status/2100884132272181594) | [X 303赞 / 20.2K浏览](https://x.com/iannuttall/status/2100884132272181594) | 笔记已收集但很难找回 | 候选检索＋相关性重排＋标签 |
| 20 | [二手商品搜索助手](https://x.com/AlanDaitch/status/2100757989212754085) | [X 952赞 / 83.9K浏览](https://x.com/AlanDaitch/status/2100757989212754085) | 大量商品信息不完整且条件各异 | 浏览器抓取＋匹配筛选＋缺失信息识别 |

### 工具、执行与调度

| 编号 | 案例／原始来源 | 本次热度 | 作者想解决的问题 | 可借用的组合 |
|---|---|---|---|---|
| 21 | [Browser Use机票搜索](https://x.com/gregpr07/status/2100411066966749359) | [X 9K赞 / 3.1M浏览](https://x.com/gregpr07/status/2100411066966749359) | 浏览网页需要大量逐步选择 | DOM状态＋候选动作＋浏览器执行 |
| 22 | [音频自动选择处理流程](https://x.com/desertantlabs/status/2102423007494889785) | [X 157赞 / 7,554浏览](https://x.com/desertantlabs/status/2102423007494889785) | 录音、会议、播客需要不同处理工具 | 本地转写/脱敏＋多问题判断＋专用工具 |
| 23 | [即时上下文压缩](https://x.com/tamarajtran/status/2100694549362553153) | [X 10K赞 / 3.8M浏览](https://x.com/tamarajtran/status/2100694549362553153) | 长会话压缩等待长、无关记录占窗口 | 历史片段＋相关性评分＋保留/删除 |
| 24 | [不确定案例升级大模型](https://x.com/nutlope/status/2100614659690713543) | [X 871赞 / 60K浏览](https://x.com/nutlope/status/2100614659690713543) | 全部用大模型慢，全部用小模型会漏判 | 快速判断＋不确定性门槛＋慢模型复查 |
| 25 | [OCR驱动桌面操作](https://x.com/milindlabs/status/2100631847155994852) | [X 2K赞 / 241.2K浏览](https://x.com/milindlabs/status/2100631847155994852) | 截图驱动每步操作成本高 | 本地界面检测/OCR＋元素选择＋点击 |
| 26 | [Agent任务调度员](https://x.com/milindlabs/status/2100515910754750741) | [X 184赞 / 14K浏览](https://x.com/milindlabs/status/2100515910754750741) | 任务来了不知道叫哪个Agent和模型 | 任务判断＋Agent候选＋模型选择 |
| 27 | [is-malicious代码扫描](https://github.com/luantak/is-malicious) | [GitHub 28★](https://github.com/luantak/is-malicious) | 陌生代码运行前难快速发现风险 | 代码片段＋风险判断＋审查提示 |
| 28 | [语音浏览器](https://github.com/moritzkremb/jev-voice-browser) | [GitHub 317★](https://github.com/moritzkremb/jev-voice-browser) | 浏览操作仍依赖鼠标与菜单 | 语音转写＋浏览状态＋动作选择 |
| 29 | [工具式即时助理](https://x.com/CodingGarden/status/2100665210419950031) | [X 1.1K赞 / 114.2K浏览](https://x.com/CodingGarden/status/2100665210419950031) | 天气、搜索、待办等要分别打开应用 | 用户意图＋工具选择＋结构化结果 |
| 30 | [YouTube赞助片段跳过](https://github.com/trungdq88/youtube-sponsor-detection) | [X 1K赞 / 82.6K浏览](https://x.com/tdinh_me/status/2100793777103466615) | 视频中的口播广告无法用普通规则定位 | 字幕/转写＋片段判断＋播放器跳转 |

### 内容、工作与判断

| 编号 | 案例／原始来源 | 本次热度 | 作者想解决的问题 | 可借用的组合 |
|---|---|---|---|---|
| 31 | [StealAds竞品广告拆解](https://x.com/TheMattBerman/status/2100654891756589230) | [X 6.8K赞 / 1M浏览](https://x.com/TheMattBerman/status/2100654891756589230) | 广告数量大，手工分析结构太慢 | 广告数据＋并行属性判断＋对比表 |
| 32 | [自然语言X信息过滤](https://x.com/marcelpociot/status/2100520134481735729) | [X 1.1K赞 / 86.2K浏览](https://x.com/marcelpociot/status/2100520134481735729) | 用户想屏蔽的是语义类型而非关键词 | 个人规则＋帖子判断＋折叠 |
| 33 | [销售线索与话术匹配](https://x.com/romanbuildsaas/status/2100891604735099103) | [X 3.4K赞 / 480.6K浏览](https://x.com/romanbuildsaas/status/2100891604735099103) | 名单和联系话术经常不匹配 | 对象信息＋消息内容＋匹配评分 |
| 34 | [通话中的销售副驾](https://x.com/moritzkremb/status/2102537239662096658) | [X 198赞 / 20.7K浏览](https://x.com/moritzkremb/status/2102537239662096658) | 通话进行时难兼顾阶段和回应线索 | 实时转写＋阶段判断＋相关提示 |
| 35 | [网站内部链接规划](https://ian.is/tools/internal-links) | [X 280赞 / 49.6K浏览](https://x.com/iannuttall/status/2102443273339994558) | 数百页面之间不知道应该互相链接什么 | 页面分类＋相关性选择＋链接清单 |
| 36 | [SuperX草稿评分](https://x.com/robj3d3/status/2100722975645598191) | [X 1.3K赞 / 239.2K浏览](https://x.com/robj3d3/status/2100722975645598191) | 发帖前缺少可重复的反馈维度 | 草稿＋多维问题＋即时修改反馈 |
| 37 | [历史帖子批量复盘](https://x.com/iannuttall/status/2100668908227162567) | [X 749赞 / 87.9K浏览](https://x.com/iannuttall/status/2100668908227162567) | 看点赞总数难理解哪些写法有效 | 帖子属性标注＋历史表现统计＋模式比较 |
| 38 | [语义网页广告拦截](https://x.com/iam_zachi/status/2100529273186472318) | [X 3.8K赞 / 207.5K浏览](https://x.com/iam_zachi/status/2100529273186472318) | 传统规则难覆盖变化的广告元素 | DOM元素＋广告判断＋页面移除 |
| 39 | [简历与职位匹配](https://x.com/sarvagya_kul/status/2100980770206879849) | [X 1.7K赞 / 150.2K浏览](https://x.com/sarvagya_kul/status/2100980770206879849) | 投递范围太大，难找真正匹配项 | 候选人资料＋岗位要求＋差异标注 |
| 40 | [Every编辑质检](https://every.to/also-true-for-humans/mini-vibe-check-typesafe-s-jev-judged-everything-i-ve-written-in-0-7-seconds) | [X 1.8K赞 / 221.3K浏览](https://x.com/danshipper/status/2099947471518474522) | 文章多，逐篇检查表达和缺陷费时 | 文稿＋编辑规则＋批量判断 |

### 游戏、仿真与连续决策

| 编号 | 案例／原始来源 | 本次热度 | 作者想解决的问题 | 可借用的组合 |
|---|---|---|---|---|
| 41 | [Minecraft双模型Agent](https://x.com/rronak_/status/2101544156757950697) | [X 7.9K赞 / 2M浏览](https://x.com/rronak_/status/2101544156757950697) | 长期计划与高频运动需要不同节奏 | 规划模型＋快速动作选择＋游戏执行 |
| 42 | [Super Mario控制](https://x.com/faadilhshaik/status/2100086301894881578) | [X 2.9K赞 / 611.3K浏览](https://x.com/faadilhshaik/status/2100086301894881578) | 逐步动作判断太慢无法跟上游戏 | 结构化游戏状态＋按键选择＋模拟器 |
| 43 | [JevPilot驾驶模拟](https://github.com/standardagents/jevpilot) | [X 4.8K赞 / 734.9K浏览](https://x.com/jpschroeder/status/2100347770867458384) | 交互环境需要持续选路径 | 轨迹候选＋Jev判断＋确定性运动控制 |
| 44 | [Doom即时控制](https://x.com/CompleteSkeptic/status/2099925687465570372) | [X 5K赞 / 1.2M浏览](https://x.com/CompleteSkeptic/status/2099925687465570372) | 动作游戏需要持续快速反应 | 文字游戏状态＋动作选择＋循环执行 |
| 45 | [jev-trader做市实验](https://github.com/jarrodwatts/jev-trader) | [X 5.1K赞 / 1.2M浏览](https://x.com/jarrodwatts/status/2100356151468585346) | 持续市场状态需要重复方向判断 | 价格状态＋买卖判断＋订单执行器 |
| 46 | [Subway Surfers控制](https://x.com/_MaxBlade/status/2100634359099232678) | [X 4.1K赞 / 360.1K浏览](https://x.com/_MaxBlade/status/2100634359099232678) | 障碍出现后需要快速选择路线 | 游戏状态＋动作候选＋连续控制 |
| 47 | [Smash Bros多角色对战](https://x.com/maubaron/status/2100738237237002706) | [X 3.6K赞 / 312.6K浏览](https://x.com/maubaron/status/2100738237237002706) | 多个角色同时需要独立动作决策 | 共享场景＋角色状态＋并行决策 |
| 48 | [游戏过程中的关卡变化](https://x.com/HugoDuprez/status/2100953089003921543) | [X 2.8K赞 / 548.7K浏览](https://x.com/HugoDuprez/status/2100953089003921543) | 固定内容无法随游戏状态改变 | 环境状态＋内容选择/组合＋关卡呈现 |
| 49 | [Jev Drone无人机仿真](https://github.com/RomanSlack/jev-drone) | [GitHub 196★](https://github.com/RomanSlack/jev-drone) | 环境变化需判断绕行、刹车或重寻目标 | 视觉预处理＋战术判断＋高频传统控制 |
| 50 | [Slay the Spire 2代玩](https://x.com/coolish/status/2100570517954838897) | [X 1.1K赞 / 334.5K浏览](https://x.com/coolish/status/2100570517954838897) | 策略游戏每一步等待模型过久 | 当前局面＋合法行动＋快速选择 |

## 热门案例共同解决了什么

这50例显示出五种反复出现的用途。以下是对样本的归纳，不是全生态统计。

1. **让固定筛选器理解人的说法。**找房、公司搜索、二手商品、语义SQL、素材检索，把“我知道我想要什么，却不知道应该点哪个字段”变成可操作的筛选和排序。
2. **让反馈发生在工作进行中。**自动标签、预测表格、启动器、WebMCP、草稿评分，减少“写完—提交—等待—发现理解错了”的来回。
3. **给多个工具分工。**音频处理、浏览器、Agent调度、不确定案例升级，快速判断负责选择，专用工具负责取数和执行，生成模型负责自由文本。
4. **把大量细小审阅变成批量判断。**邮件、文件、广告、文档包、编辑检查，都在减少人反复执行同一套模糊规则的劳动。
5. **让连续环境能持续回应。**游戏、驾驶和无人机仿真让“反复决策”变得可演示。它们很吸引注意，但演示难度、成功率和现实任务价值必须另看。

官方构建指南也明确区分了模型判断与代码工作流。Jev本身不负责自由文本生成、原始图像理解、抓网页、任意精确计算或渲染UI；这些能力来自它与其他模块的组合。[构建指南](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md) · [输入约束](https://docs.typesafe.ai/concepts/state.md)

## 六个值得一起推敲的组合机会

以下是设计假设，不能称为“全网还没人发现”。它们是这批样本没有充分展示完整闭环、但可能明显减少实际操作的方向。

### 1. 缺什么信息，就长出什么小控件

输入“周末找个地方”，先出现适合浏览的地点候选；补上“带爸妈，不想走太多”，候选按相关条件重新排，行走距离成为比较项；继续说“周日下午”，日期和营业信息接入。必要的出发地若未知，只出现一个小选择，不把用户送进整张问卷。

组合：逐字意图判断＋对象检索＋缺失条件识别＋工具参数描述＋组件选择＋真实数据。

价值：用户不需要先学会应用菜单。界面出现的每个部分都有当前任务中的用途。验证要看首次找到合适结果要几步、误解后是否好改，而不是只看动画。

### 2. 改一句话，只改变它真正影响的区域

一个比较空间里已经选了三款设备；输入“只看能带上飞机的”，只刷新相关筛选和比较维度，用户手写备注、已勾选对象和阅读位置保留。输入“把第二个发给同事”，当前对象转成分享草稿，原比较仍在。

组合：指代解析＋稳定对象身份＋条件变化判断＋依赖关系＋局部更新＋表达形式转换。

价值：连续改口仍像在操作同一个东西。这是比“每个字都整页重生成”更难也更实用的部分。需覆盖旧请求晚到、条件撤销和中文输入法中间态。

### 3. 乱资料放一起，自动找出真正需要人处理的差异

把订单、到货清单和一张商品照片放进来。系统先识别同一商品的不同叫法，再用代码精确核对数量，只展开短缺、重复和不确定的对应项。点击任一差异，都能回到原始证据。

组合：OCR/文件解析＋实体匹配＋字段映射＋确定性核算＋异常视图。

价值：节省的是每天核对信息的时间，结果可以量化验证。低置信匹配交给用户处理，不让一个貌似确定的总数掩盖错配。

### 4. 作品和依据一起变化

写一份方案时，数字、引用、图表和结论保持关系。改掉一个源数字，图表重算，相关结论被标出需要更新；其他段落继续保留。生成说明时能看到它依据哪些材料。

组合：资料检索＋来源绑定＋语义支持判断＋依赖追踪＋局部生成。

价值：减少“报告看起来更新了，里面还有旧结论”。Jev可以筛选受影响的部分，精确计算和事实校核仍有各自责任。

### 5. 让搜索同时帮助用户形成标准

用户说“想换一把舒服的椅子”，可能还不知道该比较腰托、座深还是扶手。系统从当前候选中抽出有差异的维度；用户点两把，比较项随之收敛；说“主要打游戏，桌子不高”，调整相关条件并解释排除原因。

组合：自然语言检索＋对象属性归一＋差异发现＋比较视图＋偏好反馈。

价值：不仅更快查找，还帮助用户表达尚未整理好的需求。候选属性必须来自实际资料，缺失项保持未知。

### 6. 一个工作空间能记住问题、行动和后来的结果

“这批商品为什么卖不动”形成关联具体商品的异常和待验证假设；用户选择措施后，这些关系保存。下一次导入销售数据，系统直接对照上次的问题和行动，显示哪些变化了、哪些仍无法解释。

组合：异常识别＋对象关系＋行动状态＋持久上下文＋新数据对齐。

价值：不需要每周重新向AI解释同一个业务。先验证它能少做一次手工复盘，不能把同期变化自动当成措施的因果效果。

## 万界门应优先验证什么

我倾向于先把 **1＋2＋5** 做成同一个可持续操作的空间：输入时形成候选对象；缺少条件时出现小控件；选中对象后形成比较；改口只更新关联区域。再用 **3** 测试它是否真能处理杂乱的实际资料。

空白页可以只有胶囊和淡淡的WanJie，百叶窗动效负责进入。但展开后，页面必须出现当前输入所对应的真实对象、相关数据和可操作关系。把“股票咋样了”原样复制到文稿里，没有完成这一点。

“不要预制固定东西”可以落实为：不硬编码整张股票页、购物页、行程页；准备可复用的对象、列表、比较、时间、地图、文稿和动作表达，再依据当前对象类型、条件、可用工具和用户操作状态组合。后端工具缺失时，界面表达该缺口，不伪装成已有结果。

社区中最值得拆解的参考是 [WebMCP逐字工具预测](https://github.com/sdras/jev-webmcp-extension)：它从页面提供的工具描述与参数结构构造判断，随输入更新预测，满足条件的只读查询自动执行。它没有实现万界门的全部想法，但提供了“组件和功能来自声明，输入负责选择与组合”的具体起点。

验收可用一段连续交互：输入半句话→补一个条件→选两个对象→否定前一个条件→切成比较→编辑一条备注→转成分享草稿。观察对象与备注是否保留、结果是否真实、过期请求是否被丢弃、用户是否始终知道界面为什么变了。Jev官方说明中文效果低于主要训练语言英语，因此中文半句、指代和改口必须独立测；不能据此推定本地KEV的表现。[官方state说明](https://docs.typesafe.ai/concepts/state.md)

## 逐条证据边界

以下边界与上表一起使用。项目公开存在、作者说能做某事、真实可靠运行，是三个不同的证据层次。

- **01 输入时物件浮起**：交互视频；功能细节来自收录页，原帖文字很短。[原始来源](https://x.com/heystefan_/status/2101369117496521042) · [收录页](https://madewithjev.com/builds/designer-jev)
- **02 智能复制粘贴**：演示；具体转换路径未公开核验。[原始来源](https://x.com/marcus_lowe/status/2101476399488160013) · [收录页](https://madewithjev.com/builds/smart-copy-paste)
- **03 Jev × WebMCP**：已读仓库与关键源码；需网站提供工具，未实跑。[原始来源](https://x.com/sarah_edo/status/2102025642862600634) · [收录页](https://madewithjev.com/builds/webmcp-side-panel-extension)
- **04 预测式启动器**：作者实验；约100ms为作者数据。[原始来源](https://x.com/dabit3/status/2100756930054504776) · [收录页](https://madewithjev.com/builds/predictive-launcher)
- **05 预测式电子表格**：作者实验；不是任意公式或事实计算。[原始来源](https://x.com/dabit3/status/2100780008193020049) · [收录页](https://madewithjev.com/builds/predictive-spreadsheets)
- **06 输入中自动打标签**：原帖仅简短视频介绍；逐字标签细节据目录说明，未观看视频或复跑。[原始来源](https://x.com/designgurra/status/2102726891153338374) · [收录页](https://madewithjev.com/builds/jev-auto-tagging)
- **07 X界面实时改样式**：原帖日文短句配视频；实时样式细节据目录说明，未观看视频或复跑。[原始来源](https://x.com/hedachi/status/2101952056768770247) · [收录页](https://madewithjev.com/builds/cute-x)
- **08 指向与语音画布**：功能描述来自收录页；不能推定Jev直接看图听音。[原始来源](https://x.com/jackcheng/status/2100729670991802386) · [收录页](https://madewithjev.com/builds/gesture-canvas)
- **09 自然语言计算笔记**：演示；评论指出错误，Jev不能代替确定性计算。[原始来源](https://x.com/thekitze/status/2100873520951808403) · [收录页](https://madewithjev.com/builds/jev-calc)
- **10 Drape对话试衣**：作者实验；选衣延迟不等于完整图像生成延迟。[原始来源](https://x.com/nailthy62/status/2101388186916454439) · [收录页](https://madewithjev.com/builds/drape-virtual-try-on)
- **11 下载文件自动归档**：作者演示；未验证大规模误分类率。[原始来源](https://x.com/marcelpociot/status/2100906882365788167) · [收录页](https://madewithjev.com/builds/downloads-folder-sorter)
- **12 批量邮件分类**：公开作者实验；未接触用户邮箱。[原始来源](https://x.com/rileybrown/status/2100404532119269426) · [收录页](https://madewithjev.com/builds/500-emails-3-cents)
- **13 Zillow隐含条件找房**：作者演示；只据可获得信息判断。[原始来源](https://x.com/venturetwins/status/2101341075684434245) · [收录页](https://madewithjev.com/builds/zillow-listing-search)
- **14 1kpapers论文浏览**：作者称仍在评估Jev分类，不能说线上已替换。[原始来源](https://www.1kpapers.com/) · [收录页](https://madewithjev.com/builds/1kpapers)
- **15 Ghostfeed反应视频检索**：作者产品实验；无独立检索质量评测。[原始来源](https://x.com/meetshukla_/status/2102272479674642554) · [收录页](https://madewithjev.com/builds/ghostfeed-reaction-library)
- **16 PostgreSQL语义WHERE**：作者小规模演示；不是无成本替代索引。[原始来源](https://x.com/iam_zachi/status/2100679300756435135) · [收录页](https://madewithjev.com/builds/postgres-jev-function)
- **17 DocJev文档拆包**：开源；解析后端和页面类型影响效果。[原始来源](https://github.com/jerryjliu/docjev) · [收录页](https://madewithjev.com/builds/docjev)
- **18 YC Indexor公司探索**：开源实验；部分视觉链依赖Apple Silicon。[原始来源](https://github.com/Aayan-DEV/aayans-yc-indexor) · [收录页](https://madewithjev.com/builds/yc-indexor)
- **19 keep.md搜索与标签**：作者测试；倍率不是普遍性能保证。[原始来源](https://x.com/iannuttall/status/2100884132272181594) · [收录页](https://madewithjev.com/builds/keep-md-search)
- **20 二手商品搜索助手**：作者演示；购买和联系卖家为独立动作。[原始来源](https://x.com/AlanDaitch/status/2100757989212754085) · [收录页](https://madewithjev.com/builds/second-hand-shopping-agent)
- **21 Browser Use机票搜索**：开源实验；完成搜索不等于完成预订。[原始来源](https://x.com/gregpr07/status/2100411066966749359) · [收录页](https://madewithjev.com/builds/browser-use-flights)
- **22 音频自动选择处理流程**：作者演示；“本地”不表示Jev调用也在本机。[原始来源](https://x.com/desertantlabs/status/2102423007494889785) · [收录页](https://madewithjev.com/builds/on-device-audio-pipeline)
- **23 即时上下文压缩**：作者方案；关键证据误删需要单独检验。[原始来源](https://x.com/tamarajtran/status/2100694549362553153) · [收录页](https://madewithjev.com/builds/instant-compaction)
- **24 不确定案例升级大模型**：仅100条作者测试；96/100非通用检测率。[原始来源](https://x.com/nutlope/status/2100614659690713543) · [收录页](https://madewithjev.com/builds/fraud-detection-jev-kimi)
- **25 OCR驱动桌面操作**：作者演示；文字会交给Jev，未核实完整隐私边界。[原始来源](https://x.com/milindlabs/status/2100631847155994852) · [收录页](https://madewithjev.com/builds/computer-use-without-screenshots)
- **26 Agent任务调度员**：作者演示；调度成功不等于任务完成。[原始来源](https://x.com/milindlabs/status/2100515910754750741) · [收录页](https://madewithjev.com/builds/bot-chief-of-staff)
- **27 is-malicious代码扫描**：开源小项目；判断不是安全保证。[原始来源](https://github.com/luantak/is-malicious) · [收录页](https://madewithjev.com/builds/is-malicious)
- **28 语音浏览器**：开源教学演示；支持范围未实跑。[原始来源](https://github.com/moritzkremb/jev-voice-browser) · [收录页](https://madewithjev.com/builds/jev-voice-browser)
- **29 工具式即时助理**：作者演示；不采用其“无幻觉”绝对承诺。[原始来源](https://x.com/CodingGarden/status/2100665210419950031) · [收录页](https://madewithjev.com/builds/no-llm-chat-bot)
- **30 YouTube赞助片段跳过**：开源原型；需要自己的API配置，未实跑。[原始来源](https://github.com/trungdq88/youtube-sponsor-detection) · [收录页](https://madewithjev.com/builds/youtube-sponsor-skipper)
- **31 StealAds竞品广告拆解**：作者演示；成本和速度仅其一次运行。[原始来源](https://x.com/TheMattBerman/status/2100654891756589230) · [收录页](https://madewithjev.com/builds/competitor-ad-teardown)
- **32 自然语言X信息过滤**：作者演示；可能误判，需要恢复入口。[原始来源](https://x.com/marcelpociot/status/2100520134481735729) · [收录页](https://madewithjev.com/builds/x-post-firewall)
- **33 销售线索与话术匹配**：作者实验；评分不等于真实转化率。[原始来源](https://x.com/romanbuildsaas/status/2100891604735099103) · [收录页](https://madewithjev.com/builds/lead-outreach-scoring)
- **34 通话中的销售副驾**：演示使用录制通话；成交概率未校准验证。[原始来源](https://x.com/moritzkremb/status/2102537239662096658) · [收录页](https://madewithjev.com/builds/sales-copilot)
- **35 网站内部链接规划**：作者工具；输出建议再交给其他工具实施。[原始来源](https://ian.is/tools/internal-links) · [收录页](https://madewithjev.com/builds/internal-link-tool)
- **36 SuperX草稿评分**：作者实验；不能把评分当传播保证。[原始来源](https://x.com/robj3d3/status/2100722975645598191) · [收录页](https://madewithjev.com/builds/superx-post-scoring)
- **37 历史帖子批量复盘**：作者个人数据分析；相关不等于因果。[原始来源](https://x.com/iannuttall/status/2100668908227162567) · [收录页](https://madewithjev.com/builds/x-post-analysis)
- **38 语义网页广告拦截**：作者仓库明确为实验；有误删漏删。[原始来源](https://x.com/iam_zachi/status/2100529273186472318) · [收录页](https://madewithjev.com/builds/realtime-ad-blocker)
- **39 简历与职位匹配**：作者实验；匹配分不是录用概率。[原始来源](https://x.com/sarvagya_kul/status/2100980770206879849) · [收录页](https://madewithjev.com/builds/job-match-prediction)
- **40 Every编辑质检**：作者评测；正文访问受限，细节仅作来源归属。[原始来源](https://every.to/also-true-for-humans/mini-vibe-check-typesafe-s-jev-judged-everything-i-ve-written-in-0-7-seconds) · [收录页](https://madewithjev.com/builds/every-editorial-judgments)
- **41 Minecraft双模型Agent**：固定路线、和平难度、特殊种子；非普通生存通关。[原始来源](https://x.com/rronak_/status/2101544156757950697) · [收录页](https://madewithjev.com/builds/minecraft-ender-dragon)
- **42 Super Mario控制**：作者游戏演示；未独立复跑。[原始来源](https://x.com/faadilhshaik/status/2100086301894881578) · [收录页](https://madewithjev.com/builds/jev-plays-mario)
- **43 JevPilot驾驶模拟**：Three.js模拟器，非真实自动驾驶。[原始来源](https://github.com/standardagents/jevpilot) · [收录页](https://madewithjev.com/builds/jevpilot)
- **44 Doom即时控制**：官方演示；不直接读取游戏画面。[原始来源](https://x.com/CompleteSkeptic/status/2099925687465570372) · [收录页](https://madewithjev.com/builds/jev-plays-doom)
- **45 jev-trader做市实验**：仓库默认mock/dry-run；不证明真实盈利。[原始来源](https://github.com/jarrodwatts/jev-trader) · [收录页](https://madewithjev.com/builds/jev-trader)
- **46 Subway Surfers控制**：作者演示；多局运行不等于泛化可靠。[原始来源](https://x.com/_MaxBlade/status/2100634359099232678) · [收录页](https://madewithjev.com/builds/subway-surfers)
- **47 Smash Bros多角色对战**：作者演示；计费和战绩未独立复核。[原始来源](https://x.com/maubaron/status/2100738237237002706) · [收录页](https://madewithjev.com/builds/smash-bros)
- **48 游戏过程中的关卡变化**：仅演示；不推定模型能自由生成任意代码。[原始来源](https://x.com/HugoDuprez/status/2100953089003921543) · [收录页](https://madewithjev.com/builds/realtime-game-levels)
- **49 Jev Drone无人机仿真**：MuJoCo仿真；Jev提供建议，低层代码控制安全。[原始来源](https://github.com/RomanSlack/jev-drone) · [收录页](https://madewithjev.com/builds/jev-drone)
- **50 Slay the Spire 2代玩**：作者演示；动作快不等于策略胜率高。[原始来源](https://x.com/coolish/status/2100570517954838897) · [收录页](https://madewithjev.com/builds/slay-the-spire-2)

## 另外值得保留的8个开源线索

这8个仓库为额外参考，不计入上述50例，也不与X互动数混排。均只核验公开仓库描述和星数，没有实跑。

| 仓库 | GitHub星数 | 用途 |
|---|---:|---|
| [Jev Review](https://github.com/devagrawal09/jev-review) | 618 | 代码差异或代码库审查：分阶段判断风险、选择证据、判断问题机制和严重程度，汇总到本地仪表盘。 |
| [Foreman](https://github.com/thruwire/foreman) | 571 | 在编码 Agent 运行期间，以独立观察循环判断是否偏离任务、卡住、需要验证或已完成，代码决定继续/引导/停止。 |
| [Jev Search](https://github.com/superagents-lab/jev-search) | 467 | 从自然语言判断搜索来源、查询词和时间范围，通过Search1API并行检索，再相关性排序、合并链接、流式显示。 |
| [jev-router](https://github.com/gargpratyush/jev-router) | 429 | 每次新用户回合用Jev选择Claude Code/Codex的模型档位；回合内部工具循环保持该档位。 |
| [Mobile Jev](https://github.com/droidrun/mobile-jev) | 404 | 将Android控件和已安装应用变成候选，一次判断操作和目标，通过Mobilerun执行；附实时设备界面、轨迹和任务验证。 |
| [Perch](https://github.com/lakeday-org/perch) | 185 | 语义代码lint：以自然语言规则约束方法/文件，展示问题排序，支持修复后的检查及CI门禁。 |
| [jev-semgrep / sys1grep](https://github.com/uehaj/jev-semgrep) | 144 | 逐行按语义筛选文件，支持AND/OR/NOT、跨语言查询和本地正则预筛；README已使用sys1grep名称。 |
| [Jev × WebMCP Extension](https://github.com/sdras/jev-webmcp-extension) | 117 | 由当前网页工具schema生成Jev问题，边输入边预测工具和参数；高置信只读调用自动运行，缺参数留给用户补充。 |

## 调研材料

- [50例结构化清单](selected-50.json)：原始链接、热度来源、抓取编号、用途和局限。
- [84项候选](directory-candidates.json)：保留筛选起点；未纳入不表示没有价值。
- [A组一手核验](validated-a.json)、[B组一手核验](validated-b.json)、[后段原文](validated-tail-raw.json)。
- [生态和官方能力分析](ecosystem-analysis.md)、[8个开源项目补充](ecosystem-repos.json)。
- `fetches.jsonl`、`observations.jsonl`、`cache/`记录抓取、引用和原始快照。相同作者的X帖与仓库不当作两个独立实验；性能数字仍按作者报告处理。

整理：Wilson。没有据此改动产品，也没有访问任何用户邮箱。
