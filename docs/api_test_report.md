# 接口与页面测试文档

## 1. 后台页面测试

| 页面名称       | 路径                            | 方法 | 是否正常访问 |
|:------------- |:-------------------------------|:-----|:-------------|
| 管理面板      | /admin/                        | GET  | 通过         |
| 任务管理      | /admin/tasks                   | GET  | 通过         |
| 配置管理      | /admin/config                  | GET  | 通过         |
| 日志管理      | /admin/logs                    | GET  | 通过         |
| 模板管理      | /admin/templates               | GET  | 通过         |
| 结果管理      | /admin/results                 | GET  | 通过         |

---

## 2. Google Sheet 前端页面测试

| 页面名称         | 路径                            | 方法 | 是否正常访问 |
|:--------------- |:-------------------------------|:-----|:-------------|
| Sheet参数校验首页| /google-sheet/                  | GET  | 通过         |
| 创建任务页面     | /google-sheet/create            | GET  | 通过         |
| 详情页面         | /google-sheet/detail            | GET  | 通过         |

---

## 3. API 接口测试

| 接口名称       | 地址                              | 方法 | 必选参数     | 简要说明           | 返回示例             | 是否正常  |
|:--------------|:----------------------------------|:-----|:------------|:-------------------|:---------------------|:----------|
| 任务列表      | /api/tasks                        | GET  | -           | 获取所有任务       | {"status": "success", ...}   | 通过     |
| 创建任务      | /api/tasks                        | POST | name, config| 新建并自动启动任务 | {"status": "success", ...}   | 未测POST |
| 任务详情      | /api/tasks/<task_id>              | GET  | task_id     | 获取任务详细信息   | {"status": "success", ...}   | 未测ID   |
| 取消任务      | /api/tasks/<task_id>/cancel       | POST | task_id     | 取消指定任务       | {"status": "success", ...}   | 未测POST |
| 删除任务      | /api/tasks/<task_id>              | DELETE| task_id    | 删除指定任务       | {"status": "success", ...}   | 未测DEL  |
| 任务日志      | /api/tasks/<task_id>/logs         | GET  | task_id     | 获取任务日志       | {"status": "success", ...}   | 未测ID   |
| 任务结果      | /api/tasks/<task_id>/results      | GET  | task_id     | 获取任务结果       | {"status": "success", ...}   | 未测ID   |
| 检查任务状态  | /api/tasks/<task_id>/status-check | GET  | task_id     | 本地任务状态       | {"status": "success", ...}   | 未测ID   |
| 重启任务      | /api/tasks/<task_id>/restart      | POST | task_id     | 重启任务           | {"status": "success", ...}   | 未测POST |
| 创建重启任务  | /api/tasks/<task_id>/create-restart | POST| task_id  | 基于原任务新建重启 | {"status": "success", ...}   | 未测POST |
| 确认任务继续  | /api/tasks/<task_id>/confirm      | POST | task_id,confirmed| 任务确认执行    | {"status": "success", ...}   | 未测POST |
| 配置获取      | /api/config                       | GET  | -           | 获取系统配置       | {"status": "success", ...}   | 通过     |
| 配置更新      | /api/config                       | POST | 配置内容     | 更新系统配置       | {"status": "success", ...}   | 未测POST |
| GoogleSheet配置| /api/config/google-sheet         | GET  | -           | 获取GS配置         | {"status": "success", ...}   | 通过     |
| GS配置更新    | /api/config/google-sheet          | POST | 配置内容     | 设置GS配置         | {"status": "success", ...}   | 未测POST |
| 校验配置      | /api/config/validate              | GET  | -           | 校验配置细节       | {"status": "success", ...}   | 未测     |
| Google表列表  | /api/google-sheet/worksheets      | POST | spreadsheet_id| 获取sheet页名      | {"status": "success", ...}   | 405/限POST |
| 模板列表      | /api/templates                    | GET  | -           | 获取所有模板       | {"status": "success", ...}   | 通过     |
| 新建模板      | /api/templates                    | POST | name,config | 新建模板           | {"status": "success", ...}   | 未测POST |
| 模板详情      | /api/templates/<template_id>      | GET  | template_id | 模板详细信息       | {...}                  | 未测ID   |
| 更新模板      | /api/templates/<template_id>      | PUT  | template_id,配置| 修改模板        | {"status": "success", ...}   | 未测PUT  |
| 删除模板      | /api/templates/<template_id>      | DELETE| template_id| 删除模板           | {"status": "success", ...}   | 未测DEL  |
| 结果列表      | /api/results                      | GET  | -           | 任务结果分页列表   | {"results": [...], ...}      | 通过     |
| 结果详情      | /api/results/<result_id>          | GET  | result_id   | 任务结果详情       | {...}                  | 未测ID   |
| 删除结果      | /api/results/<result_id>          | DELETE| result_id  | 删除任务结果       | {"status": "success", ...}   | 未测DEL  |
| 日志查询      | /api/logs                         | GET  | -           | 全局日志查询       | {"status": "success", ...}   | 通过     |

> 说明：部分接口参数复杂/未覆盖（如POST、DELETE或需id的接口），建议用POSTMAN或自动脚本专测。

---

## 4. 优化建议

1. 【接口幂等性】部分POST/DELETE等接口如无Token等鉴权，建议加上认证与权限。
2. 【接口文档自动化】建议使用Swagger/OpenAPI生成接口文档，便于前后端联调和测试。
3. 【错误处理统一】部分异常仅返回message，建议按统一格式返回（如code/msg/data结构）。
4. 【404与405提示】部分页面和接口GET/POST方式不符会报405，建议返回友好的错误页面或提示文案。
5. 【参数校验】建议用schema进行参数校验，前置处理避免后端逻辑报错。
6. 【API分组与版本】如接口将来要扩展，建议按/v1、/v2等API分组管理。
7. 【测试覆盖】建议所有接口提前生成用例（可pytest+Flask自测或用postman生成自动化回归）。

如需详细单接口样例请求与响应文档，可进一步扩充补充！
