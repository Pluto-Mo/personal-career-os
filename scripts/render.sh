#!/usr/bin/env bash
# render.sh — 简历 HTML → PDF + PNG，并校验「一页纸」硬约束（macOS / Linux / Git Bash）
#
# 用法:
#   bash scripts/render.sh <input.html> [输出基名] [页数上限=1]
#   applications/ 下的投递产物必须传输出基名，且不含扩展名
#
# 依赖: Chrome / Chromium / Edge 任一（无需其他安装）
set -euo pipefail

HTML="${1:?用法: render.sh <input.html> [输出基名] [页数上限]}"
NAME="${2:-}"
MAX_PAGES="${3:-1}"

# ── 定位输入输出 ──────────────────────────────────────────────
HTML_ABS="$(cd "$(dirname "$HTML")" && pwd)/$(basename "$HTML")"
OUT_DIR="$(dirname "$HTML_ABS")"
if [ -z "$NAME" ]; then
    case "$HTML_ABS" in
        */applications/*)
            echo "错误: 投递产物必须显式传入输出基名（按 JD 命名），禁止默认生成 resume.pdf" >&2
            exit 2
            ;;
        *) NAME="$(basename "$HTML_ABS" .html)" ;;
    esac
fi

case "$NAME" in
    .|..|*/*|*\\*)
        echo "错误: 输出基名不能包含路径或路径分隔符: $NAME" >&2
        exit 2
        ;;
    *.pdf|*.PDF|*.png|*.PNG)
        echo "错误: 输出基名不要包含 .pdf/.png 扩展名: $NAME" >&2
        exit 2
        ;;
esac
PDF="$OUT_DIR/$NAME.pdf"
PNG="$OUT_DIR/$NAME.png"

# file:// URL（只需处理空格；Git Bash 下用 cygpath 转成 Windows 形式）
if command -v cygpath >/dev/null 2>&1; then
    WIN_PATH="$(cygpath -m "$HTML_ABS")"          # C:/Users/.../resume.html
    FILE_URL="file:///${WIN_PATH// /%20}"
else
    FILE_URL="file://${HTML_ABS// /%20}"
fi

# ── 定位浏览器 ────────────────────────────────────────────────
BROWSER=""
for c in google-chrome chromium chromium-browser microsoft-edge msedge \
         "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
         "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
         "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
         "/c/Program Files/Microsoft/Edge/Application/msedge.exe"; do
    if command -v "$c" >/dev/null 2>&1 || [ -x "$c" ]; then BROWSER="$c"; break; fi
done
[ -z "$BROWSER" ] && { echo "错误: 未找到 Chrome/Chromium/Edge" >&2; exit 2; }

TMP_PROFILE="${TMPDIR:-/tmp}/career-os-browser-profile"
BASE_ARGS=(--headless --disable-gpu --hide-scrollbars
           "--user-data-dir=$TMP_PROFILE" --no-first-run --no-default-browser-check)

# ── 渲染 PDF + PNG ───────────────────────────────────────────
rm -f "$PDF" "$PNG"
"$BROWSER" "${BASE_ARGS[@]}" --no-pdf-header-footer "--print-to-pdf=$PDF" "$FILE_URL" 2>/dev/null
[ -f "$PDF" ] || { echo "错误: PDF 渲染失败" >&2; exit 3; }

"$BROWSER" "${BASE_ARGS[@]}" "--screenshot=$PNG" --window-size=793,1123 \
           --force-device-scale-factor=2 "$FILE_URL?clean=1" 2>/dev/null
[ -f "$PNG" ] || { echo "错误: PNG 渲染失败" >&2; exit 3; }

# ── 校验页数（一页纸硬约束） ─────────────────────────────────
# 注意: /Type /Page 常在行尾，grep 无法用 [^s] 排除 /Pages（换行不可匹配），
#       所以先匹配 /Pages? 再筛出恰好以 Page 结尾的。
PAGES="$(grep -aoE '/Type ?/Pages?' "$PDF" | grep -c 'Page$')" || PAGES=0
if [ "$PAGES" -le 0 ]; then
    PAGES="$(grep -aoE '/Count [0-9]+' "$PDF" | grep -oE '[0-9]+' | sort -n | tail -1)" || PAGES=0
    [ -n "$PAGES" ] || PAGES=0
fi

echo "PDF : $PDF"
echo "PNG : $PNG"
echo "页数: $PAGES"

if [ "$PAGES" -lt 1 ]; then
    echo "警告: 无法解析 PDF 页数，请人工打开确认。" >&2
elif [ "$PAGES" -gt "$MAX_PAGES" ]; then
    echo "错误: 内容超出 $MAX_PAGES 页（实际 $PAGES 页）！删减内容后重新渲染。" >&2
    exit 1
else
    echo "✓ 一页纸校验通过"
fi
