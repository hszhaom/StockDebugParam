# 推送通知问题分析

## 当前推送逻辑问题

### 1. execute_task 方法中的推送
- **成功推送**: 只在方法最后调用 `task_ok_to_dd` ✅
- **错误推送**: 在异常处理中调用 `error_dd` ✅
- **问题**: 对于 `get_bdl` 返回的不同状态处理不完整

### 2. get_bdl 方法中的推送缺失
- **方法返回**: 返回 `(success_count, failed_count, task_status)`
- **问题**: 没有在 `get_bdl` 方法内部进行推送通知
- **影响**: 批量处理完成时没有推送通知

### 3. 不同任务状态的处理逻辑

#### 当前逻辑分析：
```python
# 在 execute_task 中
if task_status == 'cancelled':
    # 任务被取消，保持cancelled状态
    self._log_info(f'任务已取消，成功执行: {success_count}, 失败: {failed_count}')
    return 'cancelled'  # ❌ 没有推送通知
elif task_status == 'error':
    # 任务执行出错
    self.error_dd(task.error)  # ✅ 有推送通知
    return 'error'
else:
    if stock_param is not None and stock_param != "error":
        return 'completed' if success_count > 0 else 'error'  # ❌ 没有推送通知

# 最后推送
if success_count == 0 and failed_count == 0:
    self._log_error('任务执行失败')
    return 'error'

self.task_ok_to_dd(f'成功执行: {success_count}, 失败: {failed_count}')  # ✅ 有推送通知
```

## 修复建议

### 1. 完善 get_bdl 方法的推送
- 在 `get_bdl` 方法完成时添加推送通知
- 根据不同的完成状态发送不同的通知

### 2. 统一推送逻辑
- 确保所有任务完成路径都有相应的推送通知
- 区分成功、失败、取消等不同状态

### 3. 添加详细的推送信息
- 包含成功/失败数量
- 包含任务名称和ID
- 包含查看详情的链接
