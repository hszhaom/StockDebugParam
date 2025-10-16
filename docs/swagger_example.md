openapi: 3.0.0
info:
  title: Google Sheet Task平台 API文档
  description: 自动生成的接口Swagger规范示例
  version: 1.0.0
servers:
  - url: http://127.0.0.1:5000
paths:
  /api/tasks:
    get:
      summary: 获取所有任务
      tags: [任务管理]
      responses:
        '200':
          description: 正常返回
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                  tasks:
                    type: array
                    items:
                      type: object
    post:
      summary: 创建新任务
      tags: [任务管理]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
                config:
                  type: object
              required: [name, config]
      responses:
        '200':
          description: 正常返回
  /api/tasks/{task_id}:
    get:
      summary: 获取任务详情
      parameters:
        - name: task_id
          in: path
          required: true
          schema:
            type: string
      tags: [任务管理]
      responses:
        '200':
          description: 正常返回
    delete:
      summary: 删除任务
      parameters:
        - name: task_id
          in: path
          required: true
          schema:
            type: string
      tags: [任务管理]
      responses:
        '200':
          description: 删除成功
  /api/config:
    get:
      summary: 获取系统配置
      tags: [系统配置]
      responses:
        '200':
          description: 正常返回
    post:
      summary: 更新系统配置
      tags: [系统配置]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
      responses:
        '200':
          description: 正常返回
  /api/templates:
    get:
      summary: 获取所有任务模板
      tags: [模板管理]
      responses:
        '200':
          description: 正常返回
    post:
      summary: 创建新模板
      tags: [模板管理]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
      responses:
        '200':
          description: 创建成功
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
security: []
