# Google Sheet 参数批量校验系统

一个基于 Flask 的 Google Sheet 参数批量校验系统，支持参数组合批量执行、任务管理、实时监控等功能。

## 功能特性

### 🎯 核心功能
- **参数批量校验**: 支持多参数组合的批量执行
- **Google Sheet 集成**: 直接与 Google Sheet 交互，自动写入参数和获取结果
- **任务管理**: 完整的任务生命周期管理
- **实时监控**: 基于 SSE 的实时任务状态更新
- **结果确认**: 第一次执行结果确认机制

### 🛠 管理功能
- **管理面板**: 现代化的 Web 管理界面
- **任务监控**: 实时查看任务执行状态和进度
- **配置管理**: 灵活的系统配置管理
- **日志系统**: 完整的操作日志记录
- **数据持久化**: 基于 SQLite 的数据存储

### 🎨 界面特性
- **响应式设计**: 支持桌面和移动设备
- **现代化 UI**: 基于 Bootstrap 5 的现代化界面
- **实时更新**: 无需刷新页面的实时数据更新
- **用户友好**: 直观的操作界面和交互体验

## 系统架构

### 后端架构
```
app/
├── __init__.py          # 应用工厂
├── config.py            # 配置管理
├── extensions.py        # 扩展初始化
├── models.py            # 数据模型
├── routes/              # 路由模块
│   ├── admin.py         # 管理面板路由
│   ├── api.py           # API 路由
│   └── google_sheet.py  # Google Sheet 模块路由
├── services/            # 业务逻辑服务
│   ├── task_manager.py      # 任务管理器
│   ├── google_sheet_service.py  # Google Sheet 服务
│   └── config_manager.py    # 配置管理器
└── utils/               # 工具模块
    └── logger.py        # 日志工具
```

### 前端架构
```
templates/
├── admin/               # 管理面板模板
│   ├── base.html       # 管理面板基础模板
│   ├── dashboard.html  # 仪表盘
│   ├── tasks.html      # 任务管理
│   ├── config.html     # 配置管理
│   └── logs.html       # 日志管理
└── google_sheet/       # Google Sheet 模块模板
    ├── base.html       # Google Sheet 基础模板
    ├── index.html      # 首页
    ├── create.html     # 创建任务
    └── detail.html     # 任务详情
```

## 安装和配置

### 1. 环境要求
- Python 3.8+ (本地部署)
- Docker 和 Docker Compose (Docker部署，推荐)
- pip (本地部署)

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 初始化数据库
```bash
python run.py init-db
```

### 4. 初始化默认配置
```bash
python run.py init-config
```

### 5. 启动应用
```bash
python run.py
```

应用将在 `http://localhost:5000` 启动。

### 6. Docker 部署（推荐）

#### 使用 Docker 直接部署
```bash
# 构建镜像
docker build -t google-sheet-validator .

# 运行容器
docker run -p 5000:5000 -v ./data:/app/data -v ./logs:/app/logs google-sheet-validator
```

#### 使用 Docker Compose 部署（推荐）
```bash
# 构建并启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app
```

应用将在 `http://localhost:5000` 启动。

#### Docker 环境变量配置
创建 `.env` 文件并配置以下环境变量：
```bash
SECRET_KEY=your_secure_random_key_here_at_least_32_characters_long
DATABASE_URL=sqlite:///data/app.db
FLASK_ENV=production
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT=3600
LOG_LEVEL=INFO
GOOGLE_TOKEN_FILE=data/token.json
```

## 使用指南

### 1. 访问管理面板
打开浏览器访问 `http://localhost:5000/admin/` 进入管理面板。

### 2. 配置 Google Sheet
1. 在管理面板中点击"系统配置"
2. 配置 Google Sheet 相关参数：
   - 电子表格ID
   - 工作表名称
   - Token 文件路径
   - 参数位置配置
   - 检查位置配置
   - 结果位置配置

### 3. 创建任务
1. 点击"Google Sheet"进入参数批量校验模块
2. 点击"创建新任务"
3. 填写任务配置：
   - Google Sheet 配置
   - 参数列表（JSON 数组格式）
4. 提交任务

### 4. 监控任务
- 在管理面板的"任务管理"中查看所有任务
- 实时查看任务执行状态和进度
- 查看任务日志和结果

## 配置说明

### 安全配置 (重要!)

在生产环境中，请务必设置以下环境变量：

```bash
# 生成安全的密钥 (至少32字符)
export SECRET_KEY="your_secure_random_key_here"

# 设置数据库URL
export DATABASE_URL="sqlite:///production.db"

# 其他配置
export MAX_CONCURRENT_TASKS=5
export LOG_LEVEL=INFO
```

复制 `env.example` 为 `.env` 并修改配置：
```bash
cp env.example .env
# 编辑 .env 文件设置实际的配置值
```

⚠️ **安全提醒**: 
- 永远不要在代码中硬编码密钥
- 将敏感文件添加到 `.gitignore`
- 定期轮换API密钥
- 使用HTTPS传输敏感数据

### Google Sheet 配置
```json
{
  "spreadsheet_id": "your_spreadsheet_id",
  "sheet_name": "data",
  "token_file": "data/token.json",
  "proxy_url": null,
  "parameter_positions": {
    "param1": "B6",
    "param2": "B7",
    "param3": "B8"
  },
  "check_positions": {
    "check1": "I6",
    "check2": "I7",
    "check3": "I8"
  },
  "result_positions": {
    "result1": "I15",
    "result2": "I16",
    "result3": "I17"
  }
}
```

### 参数配置示例
```json
[
  ["value1", "value2", "value3"],
  ["option1", "option2"],
  ["setting1", "setting2"]
]
```

## API 接口

### 任务管理 API
- `GET /api/tasks` - 获取所有任务
- `POST /api/tasks` - 创建新任务
- `GET /api/tasks/{task_id}` - 获取任务详情
- `POST /api/tasks/{task_id}/cancel` - 取消任务
- `GET /api/tasks/{task_id}/logs` - 获取任务日志
- `GET /api/tasks/{task_id}/results` - 获取任务结果

### 配置管理 API
- `GET /api/config` - 获取系统配置
- `POST /api/config` - 更新系统配置
- `GET /api/config/google-sheet` - 获取 Google Sheet 配置
- `POST /api/config/google-sheet` - 更新 Google Sheet 配置

### 实时事件 API
- `GET /api/tasks/{task_id}/events` - SSE 事件流
- `POST /api/tasks/{task_id}/confirm` - 确认任务继续执行

## 开发指南

### 项目结构
- `app/` - 应用核心代码
- `templates/` - 前端模板
- `static/` - 静态资源
- `data/` - 数据文件
- `logs/` - 日志文件
- `migrations/` - 数据库迁移文件

### 添加新功能
1. 在 `app/services/` 中添加业务逻辑
2. 在 `app/routes/` 中添加路由
3. 在 `templates/` 中添加前端模板
4. 更新数据库模型（如需要）

### 数据库迁移
```bash
# 创建迁移
flask db migrate -m "描述"

# 应用迁移
flask db upgrade
```

## 故障排除

### 常见问题
1. **Google Sheet 连接失败**
   - 检查 Token 文件是否正确
   - 确认电子表格ID是否正确
   - 检查网络连接和代理设置

2. **任务执行失败**
   - 查看任务日志了解具体错误
   - 检查参数格式是否正确
   - 确认 Google Sheet 权限设置

3. **页面无法访问**
   - 确认应用已正确启动
   - 检查端口是否被占用
   - 查看应用日志

### 日志查看
- 应用日志：`logs/app.log`
- 管理面板：系统日志页面
- 任务日志：任务详情页面

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进项目。

## 更新日志

### v2.0.0 (2024-01-XX)
- 重构为现代化架构
- 添加管理面板
- 改进任务管理系统
- 优化用户界面
- 增强错误处理

### v1.0.0 (2024-01-XX)
- 初始版本
- 基本的 Google Sheet 参数批量校验功能