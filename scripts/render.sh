#!/usr/bin/env bash
# render.sh — 简历 HTML → PDF + PNG，并校验「一页纸」硬约束（macOS / Linux / Git Bash）
# 用法: bash scripts/render.sh <input.html> [输出基名] [页数上限=1]

set -euo pipefail

HTML="${1:?用法: render.sh <input.html> [输出基名] [页数上限]}"
NAME="${2:-}"
MAX_PAGES="${3:-1}"
RENDER_TIMEOUT="${CAREER_OS_RENDER_TIMEOUT:-30}"

# ── 定位输入输出 ──────────────────────────────────────────────
HTML_ABS="$(cd "$(dirname "$HTML")" && pwd)/$(basename "$HTML")"
OUT_DIR="$(dirname "$HTML_ABS")"
[ -z "$NAME" ] && NAME="$(basename "$HTML_ABS" .html)"
PDF="$OUT_DIR/$NAME.pdf"
PNG="$OUT_DIR/$NAME.png"

if command -v cygpath >/dev/null 2>&1; then
    WIN_PATH="$(cygpath -m "$HTML_ABS")"
    FILE_URL="file:///${WIN_PATH// /%20}"
else
    FILE_URL="file://${HTML_ABS// /%20}"
fi

# ── 定位浏览器 ────────────────────────────────────────────────
BROWSER=""
for candidate in google-chrome chromium chromium-browser microsoft-edge msedge \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
    "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
    "/c/Program Files/Microsoft/Edge/Application/msedge.exe"; do
    if command -v "$candidate" >/dev/null 2>&1 || [ -x "$candidate" ]; then
        BROWSER="$candidate"
        break
    fi
done
[ -n "$BROWSER" ] || { echo "错误: 未找到 Chrome/Chromium/Edge" >&2; exit 2; }

# 每次渲染使用独立 profile，避免与现有浏览器或并行任务冲突。
PDF_PROFILE="$(mktemp -d "${TMPDIR:-/tmp}/career-os-pdf.XXXXXX")"
PNG_PROFILE="$(mktemp -d "${TMPDIR:-/tmp}/career-os-png.XXXXXX")"

cleanup() {
    rm -rf -- "$PDF_PROFILE" "$PNG_PROFILE"
}
trap cleanup EXIT INT TERM

BASE_ARGS=(
    --headless
    --disable-gpu
    --hide-scrollbars
    --disable-background-networking
    --disable-component-update
    --no-first-run
    --no-default-browser-check
)

# 某些 Chrome 版本会在产物已写出后继续驻留。限定等待时间；超时后
# 若目标文件已完整落盘则结束该进程并继续，否则按失败处理。
run_browser() {
    local expected="$1"
    local profile="$2"
    shift 2
    local pid
    local deadline
    local status=0
    local last_size=0
    local current_size=0
    local stable_checks=0

    "$BROWSER" "${BASE_ARGS[@]}" "--user-data-dir=$profile" "$@" >/dev/null 2>&1 &
    pid=$!
    deadline=$((SECONDS + RENDER_TIMEOUT))

    while kill -0 "$pid" 2>/dev/null; do
        if [ -s "$expected" ]; then
            current_size="$(wc -c < "$expected" | tr -d ' ')"
            if [ "$current_size" -eq "$last_size" ]; then
                stable_checks=$((stable_checks + 1))
            else
                last_size="$current_size"
                stable_checks=0
            fi

            # Chrome 偶尔在文件完成后仍驻留；文件大小连续约 1 秒不变即可收口。
            if [ "$stable_checks" -ge 5 ]; then
                kill "$pid" 2>/dev/null || true
                wait "$pid" 2>/dev/null || true
                return 0
            fi
        fi

        if [ "$SECONDS" -ge "$deadline" ]; then
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
            if [ -s "$expected" ]; then
                return 0
            fi
            echo "错误: 浏览器渲染超时，且未生成有效文件: $expected" >&2
            return 124
        fi
        sleep 0.2
    done

    wait "$pid" || status=$?
    if [ "$status" -ne 0 ] && [ ! -s "$expected" ]; then
        return "$status"
    fi
}

# ── 渲染 PDF + PNG ───────────────────────────────────────────
rm -f "$PDF" "$PNG"
run_browser "$PDF" "$PDF_PROFILE" \
    --no-pdf-header-footer "--print-to-pdf=$PDF" "$FILE_URL"
[ -s "$PDF" ] || { echo "错误: PDF 渲染失败" >&2; exit 3; }

run_browser "$PNG" "$PNG_PROFILE" \
    "--screenshot=$PNG" --window-size=793,1123 \
    --force-device-scale-factor=2 "$FILE_URL?clean=1"
[ -s "$PNG" ] || { echo "错误: PNG 渲染失败" >&2; exit 3; }

# ── 校验页数（一页纸硬约束） ─────────────────────────────────
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
