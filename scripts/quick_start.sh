#!/bin/bash
# 快速开始：批量上传视频示例脚本

echo "========================================"
echo "  视频批量上传到 OSS - 快速开始向导"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "✗ 未找到 Python3，请先安装 Python"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
python3 -c "import oss2" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠ 缺少 oss2 库，正在安装..."
    pip install oss2
fi

# 引导用户
echo ""
echo "请选择上传方式："
echo "1. 使用提示词文件上传（推荐）"
echo "2. 交互式上传（为每个视频手动输入提示词）"
echo "3. 使用文件名作为提示词"
echo ""
read -p "请输入选项 (1/2/3): " choice

read -p "视频文件夹路径: " folder

if [ ! -d "$folder" ]; then
    echo "✗ 文件夹不存在: $folder"
    exit 1
fi

case $choice in
    1)
        read -p "提示词文件路径 [scripts/prompts_example.txt]: " prompts_file
        prompts_file=${prompts_file:-scripts/prompts_example.txt}

        if [ ! -f "$prompts_file" ]; then
            echo "✗ 提示词文件不存在: $prompts_file"
            echo "你可以参考 scripts/prompts_example.txt 创建一个"
            exit 1
        fi

        python3 scripts/upload_videos_to_oss.py \
            --folder "$folder" \
            --prompts "$prompts_file" \
            --output video_urls_$(date +%Y%m%d_%H%M%S).txt
        ;;
    2)
        python3 scripts/upload_videos_to_oss.py \
            --folder "$folder" \
            --interactive \
            --output video_urls_$(date +%Y%m%d_%H%M%S).txt
        ;;
    3)
        python3 scripts/upload_videos_to_oss.py \
            --folder "$folder" \
            --output video_urls_$(date +%Y%m%d_%H%M%S).txt
        ;;
    *)
        echo "✗ 无效的选项"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "  上传完成！"
echo "========================================"
