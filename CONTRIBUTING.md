# 外部试跑与贡献指南

感谢你愿意在空闲的模型、Token 或算力额度中试跑这个项目。项目仍在验证阶段；现在最有价值的贡献通常是**可复现的问题、精炼的实验经验和小而可审查的修复**，而不是一次性扩展功能或重构。

## 先说结论

- 不要直接修改或推送原仓库的 `main`、发布分支或维护者分支。
- 请遵循：**Fork → 独立分支 → 本地试跑 → Draft Pull Request**。
- 一个分支、一个 Commit/PR 尽量只处理一个主题。
- 外部 PR 默认只是候选；只有维护者主动合并，才会影响主线。
- Agent 的长对话、模型权重、音视频大文件、密钥和隐私信息不能提交。

> 维护者可以选择仅记录 Issue、吸收经验、cherry-pick 某个 Commit、Squash 合并，或暂不采纳。代码未合并不代表反馈没有价值。

## 三种推荐参与方式

### A. 只试跑并提交问题（优先）

不改代码也很有价值。请使用 [Bug / 试跑报告模板](.github/ISSUE_TEMPLATE/bug-report.md) 创建 Issue，至少说明：项目 Commit、系统与运行环境、模型/Agent 及版本、执行命令、预期与实际结果、最小复现步骤、已脱敏的关键日志。

### B. 提交实验记录或训练素材

不要上传原始终端记录或完整 Agent 对话。请将材料整理为一个小目录，建议放在 `contributions/cases/YYYY-MM-DD-参与者-主题/`：

```text
README.md                 # 案例摘要、适用范围、基线
task.md                   # 任务目标和约束
prompt.md                 # 实际输入（已脱敏）
raw-result-summary.md     # 原始结果的精简摘要，而非完整日志
improved-result.md        # 优化后的输入/输出或方案
lessons.md                # 事实、推测、可复用规则和反例
reproduction/             # 必要的最小复现文件
```

好素材应能解释：在什么前提下、什么输入导致了什么结果、为什么成功或失败、怎样改进、在哪些场景不适用。删除重复上下文、隐私、密钥、Cookie、个人资料及版权不清晰的内容。

### C. 提交小范围修复

优先接受：可复现 Bug 的最小修复、错误信息/配置校验、跨平台兼容、测试、文档与实际行为的差异修复。提交前请先给出复现方式并保留现有行为。

未经讨论请不要提交：大规模重构、框架替换、目录大搬家、CI/CD 或发布流程修改、批量依赖升级、删除兼容逻辑、自动生成的大批量未审查代码。

## 标准流程

1. 在 GitHub 页面 Fork 本仓库，然后克隆**自己的** Fork。
2. 添加原仓库为上游并同步最新 `main`：

   ```bash
   git remote add upstream https://github.com/zxs4KHf/ai-content-creator-system.git
   git fetch upstream
   git checkout main
   git pull upstream main
   ```

3. 创建独立分支，名称建议为：

   ```text
   feedback/<名字>/<问题>
   fix/<名字>/<问题>
   docs/<名字>/<主题>
   experiment/<名字>/<主题>
   dataset/<名字>/<主题>
   ```

4. 修改前记录基线：`git rev-parse HEAD`，以及系统、硬件/运行时、依赖版本、模型与 Agent 版本、执行命令和任务目标。
5. 先不改代码地运行一次现有 Demo；确认基线后，只做本次任务必须的最小改动。
6. 提交前阅读 `git diff` 与 `git status`，检查敏感信息、绝对路径、缓存、二进制/大文件、无关格式化和未审核的 Agent 产出。
7. 用一个清晰的 Commit 提交并推送到自己的 Fork。格式建议：`fix(config): explain missing API configuration`、`feedback(agent): record loop failure`、`dataset(prompt): add refined task-splitting case`。
8. 向原仓库创建 **Draft Pull Request**，不要直接标记为 Ready for review。

## PR 要求

请使用 PR 模板并填写：

- 项目 Commit 与运行基线；
- 单一任务目标；
- 最小复现步骤、预期/实际结果；
- 修改文件与原因；
- 已运行/未运行的验证；
- 影响与回滚方式；
- Agent 参与比例和人工检查情况；
- 已确认不含密钥、Token、Cookie、账号或隐私信息。

每个 PR 只解决一个问题。发现其他问题时，请写入“额外发现”或另开 Issue，不要顺手扩大改动范围。

## Agent 硬约束

让 Agent 工作前，请将 [外部试跑 Agent 约束提示词](docs/外部试跑Agent约束提示词.md) 连同本文件提供给它。关键约束：不修改原仓库远端/权限/设置、不自动合并或发布、不碰主线、不执行破坏性系统操作、不擅自扩大任务范围，所有准备提交的差异必须由参与者人工查看。

## 不接收的内容

- 无法复现、没有环境与步骤的主观结论；
- 未精炼的完整对话、超长日志、批量生成代码；
- API Key、Token、Cookie、密码、账号、服务器信息或个人隐私；
- 大型模型、缓存、构建产物、二进制媒体；
- 未证明有使用权的训练数据、作品或声音；
- 与项目目标无关的新功能，或混合多主题的巨大改动。

## 维护者的主线保护规则

外部提交不默认合并。维护者会优先审查小而可复现的贡献，可能只采纳问题描述、案例中的规则或单个 Commit。请勿要求维护者直接接受大型 Agent 产出。

维护者应在 GitHub 的 `main` 分支保护中开启：禁止直接推送、要求 Pull Request、至少一项审批和通过必要检查；管理员也遵守该规则。此仓库的人工 G1/G2/G3 与发布确认门仍然有效，外部 PR 不得绕过它们。
