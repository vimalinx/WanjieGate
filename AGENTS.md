# WanjieGate project Agent instructions

<!-- VIMALINXOS:BEGIN managed-block project-agent-responsibility version=1 project=wanjiegate -->
## 子项目 Agent 责任边界

- 当前责任项目是注册项目 `wanjiegate`；项目身份、路径和负责人以父工作区 `governance/vimalinxos-projects.toml` 为准。
- 收到需求时先判断观察、修改、验证和最终结论是否属于本项目；只执行本项目负责的部分，不静默接管其他注册项目。
- 反思、复盘、自查或故障归因只针对当前 Agent 在本项目内的选择、改动、遗漏、证据和验证，不替其他项目、其他 Agent 或用户反思，也不推测或甩锅。
- 对其他项目或 Agent 只可陈述完成本项目任务所必需且已直接观察到的接口事实；未观察状态写 `unknown`，其诊断和修复交还对应负责人。
- 需求跨越项目边界时，完成可安全分离的本项目部分，然后向 VimalinxOS 根协调者交接外部项目、观察证据、待决定事项和应负责的 owner；子项目会话不得越界修改另一个注册项目。
- 最终答复只声明本项目内实际完成并验证的工作；AIOS 或根工作区的聚合健康不等于本项目任务完成，本项目测试也不等于外部系统已验证。

<!-- VIMALINXOS:END managed-block project-agent-responsibility -->

## Ideas 共同维护

- 涉及产品方向、架构或相关实现更新时，读取 `ideas/README.md`，将 vimalinx 与 kanemaverick 的相关提案统一纳入索引、评估和 `ideas/ROADMAP.md`。
- 按实际作者保留提案与来源；Wilson 的整理和评估单独署名。未收到的观点标为未知，不把单方建议或 Agent 评估写成双方共识。
- 更新关联提案的实现状态时附文件/提交证据；验证状态另列实际方法和范围。新方向保留旧提案并建立关联，不覆盖另一位作者的立场。
- 本目录是项目内设计资料；跨项目职责与执行权限仍遵守上面的项目边界。
