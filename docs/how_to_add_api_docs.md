# 新增接口如何编写文档（flask-restx 指南）

本文说明在本项目中为“新增或既有接口”添加/完善 Swagger 文档的步骤与规范。项目入口：`/swagger`。

## 1. 放置位置与分组
- 所有接口文档集中在 `app/routes/api_restx.py`，按功能划分为多个 Namespace：
  - 任务管理：`api_ns`
  - 系统配置：`config_ns`
  - 模板管理：`template_ns`
  - 任务结果：`result_ns`
  - 日志：`logs_ns`
  - Google Sheet：`gsheet_ns`
- 在 `app/__init__.py` 中统一注册：
  ```python
  api.add_namespace(api_ns, path='/api')
  # ... 其他分组
  ```

## 2. 新增接口的基本写法
1) 选择合适的 Namespace，例如任务相关接口归到 `api_ns`：
```python
from flask_restx import Namespace, Resource
from flask import request

api_ns = Namespace('任务管理', description='任务相关API')

@api_ns.route('/tasks/<string:task_id>/pause')
@api_ns.param('task_id', '任务ID')
class TaskPauseResource(Resource):
    @api_ns.doc('pause_task')
    def post(self, task_id):
        """暂停任务（示例）"""
        ok = do_pause(task_id)  # 你的业务逻辑
        if ok:
            return {'status': 'success'}
        return {'status': 'error', 'message': '暂停失败'}, 400
```

2) 如果需要请求体校验/示例，使用 `@api.expect` 与 `Model`：
```python
from flask_restx import fields

pause_input = api_ns.model('PauseInput', {
    'reason': fields.String(description='暂停原因', required=False)
})

@api_ns.route('/tasks/<string:task_id>/pause')
class TaskPauseResource(Resource):
    @api_ns.expect(pause_input)
    def post(self, task_id):
        data = request.get_json() or {}
        reason = data.get('reason')
        # ... 业务逻辑 ...
        return {'status': 'success', 'reason': reason}
```

3) 如果需要详细返回结构，定义响应 Model 并使用 `@api.marshal_with`：
```python
pause_resp = api_ns.model('PauseResponse', {
    'status': fields.String,
    'reason': fields.String,
})

@api_ns.route('/tasks/<string:task_id>/pause')
class TaskPauseResource(Resource):
    @api_ns.marshal_with(pause_resp, code=200, description='操作成功')
    def post(self, task_id):
        return {'status': 'success', 'reason': 'manual'}
```

## 3. 命名与注释规范
- `Namespace('中文名', description='...')`：中文可读，description 说明分组用途。
- `@api_ns.doc('operation_id')`：operation_id 建议用动宾短语、英文下划线/中划线，唯一且可检索。
- `@api_ns.param(name, desc)`：用于 path/query 参数的简要说明。
- `@api_ns.expect(model)`：请求体字段说明与必填校验（支持 required=True）。
- `@api_ns.response(code, desc)` 与 `@api_ns.marshal_with(model)`：标准化响应。
- 函数 docstring（"""..."""）尽量简洁描述该接口做什么。

## 4. 与 Blueprint 共存
- 页面（HTML 渲染）仍使用 Blueprint（如 `/admin/*`、`/google-sheet/*`）。
- API 文档统一由 restx 提供；原 `api.py` 的 Blueprint 已停用，避免路径冲突。

## 5. 常见问题排查
- `/swagger` 空白或无分组：确认 `app/__init__.py` 已 `api.add_namespace(...)` 并且服务已重启。
- 接口无参数/返回详情：补充 `@api_ns.expect`、`@api_ns.param`、`@api_ns.marshal_with`。
- 请求体验证不生效：确保使用 `Model` 并在装饰器中 `required=True`；前端选择 `application/json` 发送。

## 6. 提交与校验
- 保存改动后，重启服务并访问 `/swagger` 进行交互验证。
- 将新增/变更的接口同步到 `docs/api_overview.md`：写入一句话用途与路径。

---
如需我批量为现有接口补充更细的字段模型（包含嵌套结构、示例等），可直接提出，我可以一次性补齐。
