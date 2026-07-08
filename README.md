# Personal Career OS

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Pluto-Mo/personal-career-os?style=social)](https://github.com/Pluto-Mo/personal-career-os)

**一套跑在 AI Agent（Claude Code / Codex / Cursor 等）里的个人求职操作系统。**

核心思路一句话：**经历只沉淀一次，之后每个 JD 自动调用**——你不再维护 N 版简历，而是维护一个关于你自己的结构化记忆库，每次投递由 agent 现场定制出一页简历 + 投递邮件 + 全部配套材料，复制粘贴即可发送。

> A job-application OS that runs inside coding agents: build a structured memory of your experiences once, then have the agent tailor a one-page resume, cover email, and full application kit for every JD. Chinese-first.

---

## 快速开始（5 分钟）

```bash
# 1. Clone 仓库
git clone https://github.com/Pluto-Mo/personal-career-os.git
cd personal-career-os

# 2. 启动你的 agent（支持 AGENTS.md 规范的任意 agent）
# claude / codex / cursor ...

# 3. 对 agent 说：「帮我建库」，并粘贴你的简历
# 它会提取事实、追问细节、沉淀进 profile/

# 4. 之后投递时，直接粘贴 JD，agent 自动生成全套材料
```

**5 分钟后你就有**：
- 结构化经历库（`profile/`）
- 标准版简历（`template/resume.html`）
- 第一份定制简历 + 邮件（`applications/`）

---

## 为什么不是又一个 AI 简历工具

| 常见 AI 简历工具 | Personal Career OS |
|---|---|
| 每次从头交代背景，或维护好几版简历 | **个人经历库是持久记忆**：一次沉淀，所有投递自动调用 |
| 生成完就结束，越用越陌生 | **沉淀闭环**：投递中你确认的每个新事实自动回写经历库，越用越懂你 |
| 关键词堆砌讨好机器筛 | **价值翻译方法论**：把「我干了什么」翻译成「我为什么对你有用」，关键词对齐但不堆砌 |
| 为了好看编数字、拔头衔 | **保真铁律**：每个字可溯源到事实清单；缺数据就问你，不确认就不写——面试追问三层不露馅 |
| 「建议控制在一页内」 | **一页 A4 是硬校验**：渲染管线数 PDF 页数，超页直接报错，agent 删内容重渲而不是缩字号蒙混 |
| 只出一份简历 | **全套投递材料**：PDF + 高清 PNG（微信/手机端投递用）+ 邮件主题正文 + 作品集链接 + 投递台账 |
| **生成后手动改文件名**（每个 JD 命名要求不一样） | **自动按 JD 命名要求生成**：JD 分析自动提取命名格式（如「姓名-学校-专业」），生成时直接按要求命名，不用改来改去 |
| 绑定某个网站或某家模型 | **Agent 通用**：规范写在 `AGENTS.md`（开放标准），Claude Code、Codex、Cursor 等都能直接开工；渲染只依赖系统自带的 Edge/Chrome |
| 交互靠记命令 | **说人话就行**：粘 JD 就是投递，说「我有段新经历」就是入库，零记忆成本 |

内置方法论覆盖：中文简历的信息卫生排雷、量化改写、面试官式经历深挖、券商金融/大厂/国央企/外企四种企业性质的写法差异、投递邮件规范。

---

## 使用方式

### 0. 准备

- 任意支持 `AGENTS.md` 规范的 AI agent（Claude Code、Codex、Cursor 等）
- Chrome / Edge 浏览器（渲染 PDF/PNG 用，Windows/macOS 一般自带，无需安装依赖）

```bash
git clone https://github.com/Pluto-Mo/personal-career-os.git
cd personal-career-os
# 然后在这个目录里启动你的 agent
```

### 1. 首次使用：建库（约 10 分钟）

把你的简历（docx/pdf/文本都行）发给 agent，说：

> 帮我建库

它会走「沉淀工作流」：提取事实 → 像面试官一样问你几轮关键问题（只问事实，不问感受）→ 写成 `profile/` 下的结构化经历库，并把你的真实内容填进 `template/resume.html`（这份就是你的标准版简历）。

### 2. 日常：三个场景，直接说话

**投一个岗位** —— 把 JD 粘进对话：

> 帮我投这个岗：〔JD 全文〕

agent 会：分析 JD（硬性门槛逐条比对 + 关键词提取）→ 提出用哪几段经历、每段打什么角度（跟你确认）→ 生成一页简历渲染成 PDF/PNG → 写好邮件主题和正文 → 记入台账。产物在 `applications/日期-公司-岗位/`，你只需要复制粘贴发送。

**有了新经历**（新实习、新比赛、新证书）：

> 我上个月开始在 XX 实习了……

**某段经历太单薄**：

> 帮我挖挖 XX 那段经历

agent 用面试官的方式追问细节，把「做过 X」补成有数字的完整故事，永久沉淀。

### 3. 手动渲染（可选）

```powershell
# Windows
pwsh scripts/render.ps1 -Html template/resume.html
```
```bash
# macOS / Linux
bash scripts/render.sh template/resume.html
```

输出同目录 PDF + PNG 并校验一页纸。`resume.html` 用浏览器打开可直接预览，超一页时页面顶部出红色警告条。

---

## 它是怎么工作的

```
personal-career-os/
├── AGENTS.md            ← agent 工作规范：目录约定、意图路由、铁律（CLAUDE.md 指向它）
├── profile/             ← 你的记忆库（唯一事实源）
│   ├── _index.md        ← 经历总索引：标签 + 完整度，agent 投递时先读这里
│   ├── basics.md / links.md / preferences.md
│   └── experiences/     ← 一段经历一个文件：事实清单 + 现成表述 + 待挖掘
│       └── _TEMPLATE.md ← 格式模板（agent 参考用，不要删除）
├── methodology/         ← 方法论：简历方法论 / 风格库（按企业性质）/ 岗位速查（12 个岗位规范）/ 挖掘问题库
├── workflows/           ← 三大工作流的执行手册：apply（投递）/ intake（沉淀）/ dig（深挖）
├── template/resume.html ← 唯一简历模板 = 你的标准版简历（A4 一页，自带超页警告）
├── scripts/             ← render.ps1 / render.sh：HTML → PDF + PNG + 一页硬校验
└── applications/        ← 每次投递一个目录（简历 + JD 分析 + 邮件 + 笔记）+ 台账 _log.md
```

数据流：`JD 进来 → 读 _index 挑经历 → 与你确认角度 → 按方法论改写 → 渲染校验一页 → 全套材料落盘 → 新事实回写 profile`。

---

## 隐私提醒

`profile/`、`applications/`、`template/resume.html` 建库后全是你的个人数据。**不要把填了真实信息的仓库公开推送**——建议 fork/clone 后把远端设为私有仓库，或者不设远端纯本地使用。

---

## 常见问题

### 如何备份我的数据？

所有个人数据在 `profile/`、`template/`、`applications/` 下。定期备份这些目录即可。建议：

```bash
# 方式1：用 git 管理（推荐，但要设为私有仓库）
git init
git add profile/ template/ applications/
git commit -m "backup"

# 方式2：直接复制目录到云盘或 U 盘
```

### 如何切换到其他 agent？

本项目采用 `AGENTS.md` 开放规范，任何支持该规范的 agent 都能使用。只需：
1. 在项目目录下启动新 agent
2. 直接开始对话（无需额外配置）

已测试支持：Claude Code、Codex、Cursor。

### 如果简历超过一页怎么办？

渲染脚本会自动检测并报错。按优先级删减内容：
1. 删除弱相关经历
2. 压缩 bullet 数量（每段经历 2-3 条即可）
3. 删除不必要的技能或爱好

**禁止**把字号降到 10pt 以下来强行塞内容。

### 如何回退到之前的简历版本？

每次投递都会在 `applications/日期-公司-岗位/` 下保存完整简历。需要回退时：
1. 找到对应目录的 `resume.html`
2. 复制回 `template/resume.html`

### 脱敏检查脚本报错怎么办？

说明当前仓库中存在敏感信息。按脚本提示检查对应文件，确认：
- 是否是真实个人信息（手机号、邮箱等）
- 如果是，删除或替换为占位符（如 `138-0000-0000`、`example@test.com`）
- 如果是误报（如文档中的示例数据），可以忽略

### 方法论内容可以修改吗？

可以。`methodology/` 下的内容是可执行的指导原则，欢迎根据自己的实践优化。改完后：
1. 确保 agent 仍能按新表述操作（保持「可执行」特性）
2. 考虑提交 PR 分享给其他用户（见 [贡献指南](CONTRIBUTING.md)）

---

## 社区与贡献

欢迎参与贡献！

- **报告问题**：[创建 Issue](../../issues/new?template=bug_report.md)
- **功能建议**：[创建 Issue](../../issues/new?template=feature_request.md)
- **方法论贡献**：[创建 Issue](../../issues/new?template=methodology_contribution.md)
- **代码贡献**：阅读 [贡献指南](CONTRIBUTING.md) 后提交 PR

查看 [使用案例](docs/EXAMPLES.md) 了解三大工作流的完整对话示例。

---

## 致谢与许可

- 方法论框架受 [industry-resume-toolkit](https://github.com/shangsitongshizaitiantang/industry-resume-toolkit)（HR 顾问视角的简历方法论）与 [Resume-Tailor-AI](https://github.com/JaimeYeung/Resume-Tailor-AI)（Fact Bank 思想）启发，本仓库全部内容为原创提炼表述。
- License: [MIT](LICENSE)

---

**Star History**

[![Star History Chart](https://api.star-history.com/svg?repos=Pluto-Mo/personal-career-os&type=Date)](https://star-history.com/#Pluto-Mo/personal-career-os&Date)

