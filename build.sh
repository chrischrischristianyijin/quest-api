#!/bin/bash
# Render 部署构建脚本

echo "🚀 开始 Quest API 构建..."

# 设置 NLTK 数据目录
export NLTK_DATA="/opt/render/nltk_data"
mkdir -p $NLTK_DATA

# 更新 pip
echo "📦 更新 pip..."
pip install --upgrade pip

# 安装基础依赖
echo "📦 安装基础依赖..."
pip install -r requirements.txt

# 初始化 NLTK 数据（兼容 NLTK 3.8+）
echo "📚 初始化 NLTK 数据..."
python -c "
import nltk
from packaging.version import Version

# 设置 NLTK 数据路径
nltk.data.path.append('/opt/render/nltk_data')

print('下载 NLTK punkt 数据...')
nltk.download('punkt', quiet=True)

# NLTK 3.8+ 需要 punkt_tab
try:
    if Version(nltk.__version__) >= Version('3.8'):
        print('下载 NLTK punkt_tab 数据...')
        nltk.download('punkt_tab', quiet=True)
    else:
        print('NLTK 版本 < 3.8，跳过 punkt_tab')
except Exception as e:
    print(f'punkt_tab 下载跳过: {e}')

print('下载 NLTK stopwords 数据...')
nltk.download('stopwords', quiet=True)

print('NLTK 数据初始化完成')
"

echo "✅ 构建完成！"
