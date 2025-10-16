# API 概览

> 本文提供当前可用接口的简要说明，完整交互与字段请访问 `/swagger`。

## 任务管理（/api）
- GET /tasks：获取所有任务（内存/数据库状态汇总）。
- POST /tasks：新建任务并尝试自动启动，入参含 name、config 等。
- GET /tasks/{task_id}：获取指定任务详情与状态。
- DELETE /tasks/{task_id}：删除任务。
- POST /tasks/{task_id}/cancel：取消任务。
- GET /tasks/{task_id}/logs：获取任务日志（由任务管理器维护）。
- GET /tasks/{task_id}/results：获取任务产出结果。
- GET /tasks/{task_id}/status-check：检查本地进程/状态，判断可否恢复。
- POST /tasks/{task_id}/restart：重启任务（可选择从检查点恢复）。
- POST /tasks/{task_id}/create-restart：基于原任务创建一个“重启任务”并尝试启动。
- POST /tasks/{task_id}/confirm：SSE流程中的“确认继续执行”指令。
- GET /tasks/{task_id}/events：SSE事件流（实时状态、心跳、确认请求）。

## 系统配置（/api）
- GET /config：获取系统配置（调用前刷新缓存）。
- POST /config：更新系统配置并立即刷新缓存生效。
- GET /config/google-sheet：获取 Google Sheet 相关配置。
- POST /config/google-sheet：更新 Google Sheet 相关配置。
- POST /config/refresh：强制刷新配置缓存。
- GET /config/validate：对比数据库配置、缓存与 Google Sheet 配置。

## 模板管理（/api）
- GET /templates：获取所有任务模板（按创建时间倒序）。
- POST /templates：创建任务模板（name、config 必填）。
- GET /templates/{template_id}：模板详情。
- PUT /templates/{template_id}：更新模板。
- DELETE /templates/{template_id}：删除模板。

## 任务结果（/api）
- GET /results：分页获取任务结果，可按 `task_id` 过滤。
- GET /results/{result_id}：任务结果详情。
- DELETE /results/{result_id}：删除任务结果。

## 日志（/api）
- GET /logs：全局日志查询（按级别、关键词、日期过滤，支持任务ID过滤）。
- GET /logs/latest：获取最新增量日志（since 之后）。
- GET /tasks/{task_id}/system-logs：按任务ID抽取系统日志并按时间排序。

## Google Sheet（/api）
- POST /google-sheet/worksheets：传入 `spreadsheet_id` 返回所有工作表名称，支持 token/proxy 设置。

> 页面路由（`/admin/*`、`/google-sheet/*`）保持 Blueprint 方式；API 文档由 flask-restx 统一管理。
