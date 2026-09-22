# 跨境电商多语言智能客服与运营Agent

## 项目结构

```
MultilingualAgent/
├── backend/                 # 后端 (FastAPI + Python)
│   ├── app/                 # 应用代码
│   │   ├── api/             # API路由
│   │   ├── middleware/      # 中间件
│   │   ├── models/          # 数据模型
│   │   ├── rag/             # RAG检索
│   │   ├── services/        # 业务逻辑
│   │   └── utils/           # 工具函数
│   ├── scripts/             # 脚本工具
│   ├── data/                # 数据文件 (违禁词库)
│   ├── logs/                # 日志文件 (自动创建)
│   ├── test_data/           # 测试数据
│   ├── .env                 # 环境变量
│   ├── requirements.txt     # Python依赖
│   └── init-db.sql          # 数据库初始化
│
├── frontend/                # 前端 (React + TypeScript)
│   ├── src/                 # 源代码
│   │   ├── api/             # API接口层
│   │   ├── components/      # React组件
│   │   └── types/           # TypeScript类型
│   ├── dist/                # 构建产物
│   ├── package.json         # Node依赖
│   └── vite.config.ts       # Vite配置
│
├── docker-compose.yml       # Docker编排
└── README.md                # 项目说明
```

## 快速开始

### 后端启动

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 前端启动

```bash
cd frontend
npm install
npm run dev          # 开发模式
npm run build        # 构建生产版本
```

## 技术栈

- **后端**: FastAPI + PostgreSQL + Redis + LangChain
- **前端**: React 18 + TypeScript + Vite + Tailwind CSS
- **部署**: Docker Compose

## 功能模块

1. **多语言客服Agent** - 6语言智能对话
2. **意图识别** - 7种意图分类
3. **转人工机制** - 低置信度自动转人工
4. **合规过滤** - 违禁词双通道过滤
5. **Listing生成** - Amazon/Temu/TikTok Shop
6. **评论分析** - 情感分析 + 主题聚类
7. **广告词生成** - 4种广告类型
8. **运营报表** - 数据可视化仪表盘