# 实验室预约 Agent v2 设计思路与整体实现

## 1. 目标

本次改造目标是把 Agent 从“单轮问答”升级为“可循环执行任务”的流程化 Agent，核心链路如下：

用户输入 -> LLM 规划下一步 -> 调用工具 -> 获取结构化结果 -> 再规划 -> 再调用工具 -> 完成任务

## 2. 架构分层

1. 入口层：`POST /api/agent/chat`，统一接收自然语言请求。
2. 规划层（Planner）：`_llm_agent_decide`，只负责输出下一步动作 JSON，不直接改数据库。
3. 工具层（Tool Executor）：`_run_tool`，统一执行白名单工具并返回结构化结果。
4. 会话层（Memory）：`AGENT_SESSIONS`，维护预约表单、最近实验室列表、最近预约列表。
5. 循环控制层：`_agent_loop`，负责最大步数、重复工具限制、失败回退。

## 3. 协议设计

### 3.1 Planner 输出协议

```json
{
  "tool": "query_labs | query_schedule | recommend_time | create_reservation | my_reservations | cancel_reservation | navigate | ''",
  "params": {},
  "reply": "给用户看的文本",
  "done": false
}
```

### 3.2 Tool 结果协议

```json
{
  "ok": true,
  "tool": "create_reservation",
  "data": "结果摘要文本",
  "error_code": "",
  "error_message": ""
}
```

### 3.3 Chat 最终返回

```json
{
  "reply": "最终回复",
  "actions": [],
  "trace_id": "agt-xxxx"
}
```

## 4. 工具白名单

当前已实现工具：

1. `query_labs`
2. `query_schedule`
3. `recommend_time`
4. `create_reservation`
5. `my_reservations`
6. `cancel_reservation`
7. `navigate`

并通过 `AGENT_TOOL_SCHEMAS` 做入参校验，避免 Planner 产生非法工具调用。

## 5. 关键控制策略

1. 最大循环步数：`MAX_AGENT_STEPS = 5`。
2. 同工具重复保护：`MAX_TOOL_REPEAT_STEPS = 2`。
3. 缺参即时追问：`missing_fields` 直接返回最小补充问题。
4. 业务失败可解释：统一 `error_code/error_message`。
5. 非实验室问题自动回退通用对话模型（若配置可用）。

## 6. 会话记忆设计

会话结构包含：

1. `reservation_form`：日期、时段、人数、用途、lab_id、校区、类型。
2. `last_labs`：最近查询实验室，用于“输入数字选第N个实验室”。
3. `last_reservations`：最近预约记录，用于“输入数字选第N条预约取消”。

## 7. 规则兜底

当 LLM 不可用或循环失败时，走 `_fallback_rule_chat`：

1. 关键意图识别：查实验室/查排期/创建预约/我的预约/取消预约/导航。
2. 仍能通过工具层完成核心流程，不依赖 LLM 才能工作。

## 8. 已改动代码文件

1. `lab/backend/app/services/agent_service.py`

主要变更包括：

1. 重写 Agent 主体为循环规划架构。
2. 新增统一协议（Planner 输出 + Tool 输出 + Chat 输出）。
3. 新增 `cancel_reservation` 工具。
4. 新增 `trace_id` 便于链路追踪和调试。
5. 新增工具参数白名单和缺参提示。

## 9. 校验结果

已执行编译校验：

1. `python -m py_compile lab/backend/app/services/agent_service.py`
2. `python -m py_compile lab/backend/app/api/agent.py`
3. `python -m py_compile lab/backend/app/services/reservation_service.py`

均通过。


用户输入
   ↓
_extract_form_from_text（规则解析）
   ↓
_llm_extract_form（LLM补全表单）
   ↓
_llm_agent_decide（决定做什么）
   ↓
_auto_fill_params（补工具参数）
   ↓
_run_tool（执行工具）
   ↓
_tool_result（返回结果）