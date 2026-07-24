# 多格式导出工作流（export）

> 触发：用户要 Word/DOCX、PDF、PNG/图片，或需要完整投递包。
> 目标：从同一份定稿 HTML 生成内容一致、版式正确、恰好一页的 DOCX/PDF/PNG。

## 1. 确定内容源与版式

- 标准版使用 `template/resume.html`；岗位版使用对应 `applications/<日期-公司-岗位>/resume.html`。
- 用户没有指定版式时，固定沿用 `template/resume.html` 的 A4 三栏页眉、分节线、经历标题/日期和项目符号结构，只替换内容并按事实增删区块；字体、字号、边距、间距和线条严格执行 `methodology/默认简历版式规范.md`。
- 用户明确提供其他模板时才改变视觉结构；不得把参考模板中的姓名、照片、校徽或经历复制给其他用户。
- HTML 是三种格式共同的内容源。先定稿内容，再导出；禁止分别手改 DOCX、PDF、PNG 造成内容漂移。

### 1a. 先确认选做图片

生成前必须向用户展示两个互相独立的选择，不能把图片当成默认模板的一部分：

- 证件照：`上传并使用` / `使用已确认文件` / `不使用`。只能使用用户提供的文件，禁止搜索、生成或从其他材料中擅自截取
- 学校校徽：`上传并使用` / `使用已确认文件` / `帮我搜索` / `不使用`。只有用户明确选择“帮我搜索”时才进行 Web Search

搜索校徽时优先学校官方网站；展示候选图片及来源链接，核对学校全称和校区，等用户确认具体候选后再下载。搜索不到可靠候选就如实说明，让用户选择上传或不使用，禁止拿相似学校或非官方图标代替。

用户确认使用后，将原图转换为固定画布：

```text
python scripts/prepare-resume-image.py portrait "<用户证件照>" "<目录>/portrait.standard.png"
python scripts/prepare-resume-image.py logo "<已确认校徽>" "<目录>/school-logo.standard.png"
```

- 证件照最终图片框：20 mm × 27 mm
- 校徽最终图片框：32 mm × 18 mm
- 转换只做旋转纠正、等比缩放、居中和留白，不拉伸、不裁脸
- 用户选择“不使用”时，不在 HTML 中插入对应 `<img>`；保持空白即可

## 2. 确定文件名

- DOCX、PDF、PNG 使用同一个输出基名。
- JD 有命名要求时按 JD；否则使用 `学校-姓名-专业-年级`。
- 投递目录下禁止使用 `resume`、`未命名`等临时名称交付。

## 3. 生成 PDF 与同源 PNG

- macOS/Linux：`bash scripts/render.sh "<resume.html>" "<输出基名>"`
- Windows：`pwsh scripts/render.ps1 -Html "<resume.html>" -Name "<输出基名>"`
- 脚本先生成并确认 PDF 恰好一页，再从最终 PDF 栅格化 PNG；不得直接截取浏览器页面冒充最终图片。
- 查看 PNG，依据默认版式规范检查中文字体、字号层级、四边边距、分割线、区块间距、项目符号、日期、换行、裁切和留白；图片仅在用户选择使用时检查。

## 4. 生成并校验 DOCX

使用当前 Agent 中包含 `python-docx` 的文档运行时：

```text
python scripts/export-docx.py "<resume.html>" "<输出基名>.docx"
```

不要用 LibreOffice 直接把 HTML 转成 DOCX。脚本会用原生 Word 结构重建三栏页眉、段落、日期右对齐、分节线和项目符号。

生成后必须使用当前 Agent 的 DOCX 渲染能力将其渲染为逐页 PNG，并逐页检查：

```text
python scripts/verify-docx.py "<输出基名>.docx" --output-dir "<临时 QA 目录>"
```

脚本会处理 macOS 的中文字体映射、强制检查恰好一页，并生成 `page-1.png`。如果宿主 Agent 有更可靠的原生 Word 渲染器，也可以额外复核，但不能跳过页数和目视检查。

1. 只能产生 `page-1.png`；出现 `page-2.png` 即失败
2. 不得有方框字、缺字、重叠、裁切、日期掉行、分割线漂移、边距变化、图片拉伸或项目符号错位
3. DOCX 文本必须与 HTML/PDF 一致，不得遗漏或新增事实

DOCX 超页或错版时，调整共同内容源或 DOCX 导出参数，然后重新生成并检查三种格式；禁止只把 Word 字号缩到 10pt 以下。

## 5. 交付门槛

只有同时满足以下条件才能汇报完成：

- DOCX：一页，最新渲染图已目视通过
- PDF：一页，最新渲染已通过
- PNG：来自该 PDF，只有一张 A4 图片，最新图片已目视通过
- 三种格式内容一致、输出基名一致

交付最终 DOCX/PDF/PNG；内部 DOCX QA 图片不作为最终产物，除非用户明确要求。
