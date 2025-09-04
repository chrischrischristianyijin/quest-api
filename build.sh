#!/bin/bash
# Render 部署构建脚本

echo "🚀 开始 Quest API 构建..."

# 更新 pip
echo "📦 更新 pip..."
pip install --upgrade pip

# 安装基础依赖
echo "📦 安装基础依赖..."
pip install -r requirements.txt

# 尝试初始化 NLTK 数据（如果 Sumy 可用）
echo "📚 初始化 NLTK 数据..."
python -c "
try:
    import nltk
    print('下载 NLTK punkt 数据...')
    nltk.download('punkt', quiet=True)
    print('NLTK 数据初始化完成')
except Exception as e:
    print(f'NLTK 初始化跳过: {e}')
    print('这是正常的，系统会使用简单的文本处理')
"

echo "✅ 构建完成！"
