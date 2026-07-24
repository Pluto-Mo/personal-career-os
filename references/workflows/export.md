# 产物导出工作流（export）

> 触发：用户要导出标准版或某个岗位版简历，或完整投递包需要生成 Word、PDF、图片和投递正文。
> 目标：从同一份已确认内容生成可编辑、可打印、可直接发送的多格式产物，不让各格式内容漂移。

路径统一按根目录 `SKILL.md` 的 `SKILL_ROOT` / `CAREER_ROOT` 约定解析。

## 1. 确定版本

- 用户点名了岗位、公司或 application 目录 → 使用该目录的 `resume.html`。
- 用户说“标准版”“当前简历” → 使用 `template/resume.html`。
- 同时存在多个候选且无法判断 → 只问一句，让用户选标准版或具体岗位版。
- HTML 仍是当前版本的已确认内容源；先完成事实、措辞和顺序修改，再导出其他格式。

## 2. 确定格式与文件名

- “Word”表示 `.docx`；“图片”默认 `.png`。
- 用户明确指定格式时，只交付指定格式；生成过程所需的 HTML 可以保留在工作区。
- 用户说“完整投递包”时，生成：HTML、DOCX、PDF、PNG、`email.md`、`jd.md`、`notes.md`。
- 标准版首次生成时，默认生成：HTML、DOCX、PDF、PNG。
- DOCX、PDF、PNG 使用同一文件基名；JD 有命名要求时优先遵守，否则使用投递工作流的默认命名。

## 2a. 确认页眉视觉素材

在实际生成前，必须分别确认两个独立选择；即使用户说“直接出”，也不能跳过：

- 证件照：`上传并使用` / `使用已确认文件` / `不使用`。只能使用用户提供的文件，禁止搜索、生成或从其他材料擅自截取。
- 学校校徽：`上传并使用` / `使用已确认文件` / `帮我搜索` / `不使用`。只有用户明确选择“帮我搜索”时才能检索；优先学校官网，展示候选来源并等用户确认具体图片后再使用。

两项可以只选其一或都不使用。将选择、原始文件、标准化文件及校徽来源记录进基础信息。用户选择“不使用”时，HTML 和 DOCX 的对应页眉位置保持为空。

对确认使用的本地图片，先用当前 Agent 的文档 Python 标准化；不得覆盖用户原图：

```text
python "$SKILL_ROOT/scripts/prepare-resume-image.py" portrait "<用户证件照>" "<输出目录>/portrait.standard.png"
python "$SKILL_ROOT/scripts/prepare-resume-image.py" logo "<已确认校徽>" "<输出目录>/school-logo.standard.png"
```

- 证件照固定图片框为 20 mm × 27 mm；校徽固定图片框为 32 mm × 18 mm。
- 处理仅做旋转纠正、等比缩放、居中和留白；不拉伸、不裁脸。
- 仅在用户确认使用后，才把对应 `<img>` 加入简历 HTML；DOCX 导出会从同一 HTML 读取图片。

## 3. 生成 PDF 与 PNG

- macOS/Linux：`bash "$SKILL_ROOT/scripts/render.sh" "$SOURCE_HTML" "$FILE_BASENAME"`
- Windows：`pwsh "$SKILL_ROOT/scripts/render.ps1" -Html "$SOURCE_HTML" -Name "$FILE_BASENAME"`

确认 PDF 恰好一页，并查看 PNG 检查中文、换行、边界、日期和项目符号。素材不满一页可以留白，不要注水；超页时删减弱相关内容，不把字号降到 10pt 以下。

## 4. 生成 Word

使用包含 `python-docx` 的当前 Agent 文档运行时执行：

```text
python "$SKILL_ROOT/scripts/export-docx.py" "$SOURCE_HTML" "$OUTPUT_DOCX"
```

- Codex 中先使用 workspace dependency loader 获取文档 Python；其他 Agent 优先使用自己的文档创建能力。
- 不要求最终用户手动安装 Python 包。
- 不要用 LibreOffice 直接把 HTML 转 DOCX；CSS/flexbox 与中文字体会产生不可接受的损坏。
- 脚本从定稿 HTML 提取姓名、联系方式、区块、经历标题、日期、详情和 bullet，再用原生 Word 结构重建，因此 DOCX 与 PDF/PNG 使用同一份内容。

## 5. 校验 Word

1. 确认 DOCX 是有效 OOXML，包含 A4 页面设置、区块标题、右对齐日期和真实项目符号。
2. 从 DOCX 提取文本，对照 HTML 核验姓名、日期、数字、头衔和每条 bullet，没有遗漏或新增事实。
3. 使用当前 Agent 的文档渲染能力把 DOCX 渲染为逐页图片，查看所有页面；必须检查中文方框、换行、日期对齐、区块线和溢出。
4. 默认要求一页。若宿主环境没有可靠的 DOCX 渲染能力，可以交付结构校验通过的 DOCX，但必须明确说明尚未完成 Word 视觉校验，不能把损坏的转换文件冒充成已验证产物。

## 6. 生成投递正文

只有存在具体 JD 或用户明确要求时才生成 `email.md`。内容包括：

- 邮件主题；
- 200 字以内的邮件正文；
- 一段更短的平台私信/微信投递正文；
- 附件清单与文件名。

所有匹配点必须来自 profile 中已确认的事实。

## 7. 汇报

用用户可读标签交付每种成品（如“可编辑 Word 简历”“正式 PDF 简历”“手机端图片”“邮件正文”），说明用途与未完成的验证。不要向用户展示内部路径、实际文件名、QA 图片或临时文件，除非用户明确要求。
