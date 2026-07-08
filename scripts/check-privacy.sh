#!/usr/bin/env bash
# 脱敏检查脚本 - Bash 版本
# 用途：在 push 到公开仓库前检查是否有敏感信息泄漏

set -e

ERROR_COUNT=0
WARNING_COUNT=0
VERBOSE=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

echo "=== Personal Career OS 脱敏检查 ==="
echo ""

# 定义需要检查的目录和文件
CHECK_PATHS=(
    "profile/"
    "template/"
    "applications/"
    "README.md"
    "AGENTS.md"
)

# 定义敏感信息模式
declare -A PATTERNS=(
    ["手机号"]="1[3-9][0-9]{9}"
    ["身份证"]="[0-9]{17}[0-9Xx]"
)

# 检查函数
check_file() {
    local file="$1"
    local rel_path="${file#./}"
    local has_issues=false
    local is_template=false

    # 跳过二进制文件
    if file "$file" | grep -q "text"; then
        local content
        content=$(cat "$file")

        # 检查是否仍是模板状态
        if echo "$content" | grep -qE "【待填】|张三|zhangsan@example.com|138-0000-0000"; then
            is_template=true
        fi

        # 检查手机号
        if echo "$content" | grep -qE '\b1[3-9][0-9]{9}\b'; then
            echo "  [错误] $rel_path: 发现手机号"
            ((ERROR_COUNT+=1))
            has_issues=true
            if [ "$VERBOSE" = true ]; then
                echo "$content" | grep -nE '\b1[3-9][0-9]{9}\b' | head -3 | sed 's/^/    /'
            fi
        fi

        # 检查邮箱（排除示例域名）
        if echo "$content" | grep -E '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b' | grep -vE 'example\.com|test\.com|demo\.com|placeholder'; then
            local real_emails
            real_emails=$(echo "$content" | grep -oE '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b' | grep -vE 'example\.com|test\.com|demo\.com|placeholder' || true)
            if [ -n "$real_emails" ]; then
                echo "  [警告] $rel_path: 疑似真实邮箱"
                ((WARNING_COUNT+=1))
                has_issues=true
                if [ "$VERBOSE" = true ]; then
                    echo "$real_emails" | head -3 | sed 's/^/    /'
                fi
            fi
        fi

        # 检查身份证
        if echo "$content" | grep -qE '\b[0-9]{17}[0-9Xx]\b'; then
            echo "  [错误] $rel_path: 发现身份证号"
            ((ERROR_COUNT+=1))
            has_issues=true
        fi

        # 检查银行卡号
        if echo "$content" | grep -qE '\b[0-9]{16,19}\b'; then
            local potential_cards
            potential_cards=$(echo "$content" | grep -oE '\b[0-9]{16,19}\b' | head -1 || true)
            if [ -n "$potential_cards" ]; then
                echo "  [警告] $rel_path: 疑似银行卡号（16-19位数字）"
                ((WARNING_COUNT+=1))
                has_issues=true
            fi
        fi

        # 模板状态记录（静默）

        if [ "$has_issues" = true ]; then
            echo ""
        fi
    fi
}

# 遍历检查
echo "检查中..."
FILES_CHECKED=0

for path in "${CHECK_PATHS[@]}"; do
    if [ -e "$path" ]; then
        if [ -d "$path" ]; then
            while IFS= read -r -d '' file; do
                # 跳过二进制文件和临时文件
                case "$file" in
                    *.png|*.jpg|*.pdf|*/tmp/*|*/.git/*)
                        continue
                        ;;
                esac
                check_file "$file"
                ((FILES_CHECKED+=1))
            done < <(find "$path" -type f -print0)
        elif [ -f "$path" ]; then
            check_file "$path"
            ((FILES_CHECKED+=1))
        fi
    fi
done

echo ""
echo "=== 检查结果 ==="
echo "已检查文件: $FILES_CHECKED 个"
echo ""

if [ $ERROR_COUNT -gt 0 ]; then
    echo "[失败] 发现 $ERROR_COUNT 个错误，$WARNING_COUNT 个警告"
    echo "请检查以上文件，移除敏感信息后重新运行。"
    exit 1
elif [ $WARNING_COUNT -gt 0 ]; then
    echo "[警告] 发现 $WARNING_COUNT 个警告"
    echo "请确认以上内容是否为真实敏感信息。"
    echo "如果确认无误，可以继续。"
    exit 0
else
    echo "[通过] 未发现敏感信息"
    exit 0
fi
