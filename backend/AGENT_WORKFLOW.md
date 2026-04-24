# Agent 智能预约流程说明

本文档用于毕业设计答辩，说明实验室预约系统中 Agent 模块的整体设计、预约流程、关键函数和实现思路。

## 1. 模块定位

本系统中的 Agent 是一个面向实验室预约场景的智能助手。它不是直接由大模型操作数据库，而是采用：

```text
DeepSeek 规划决策 + 后端业务工具执行 + 服务层规则校验
```

也就是说，DeepSeek 主要负责理解用户自然语言、判断下一步该做什么、整理自然回复；真正的预约创建、冲突检测、权限校验和数据库写入仍然由后端服务层完成。

这种设计的好处是：

- 大模型负责自然语言理解，提升交互体验。
- 后端服务负责业务规则，保证系统安全和数据一致性。
- DeepSeek 不直接修改数据库，降低误操作风险。
- 当 LLM 不可用时，系统仍可降级到规则引擎完成基础功能。

## 2. 入口位置

Agent 的接口入口位于：

```text
backend/app/api/agent.py
```

前端调用：

```http
POST /api/agent/chat
```

核心业务入口函数位于：

```text
backend/app/services/agent_service.py
```

核心函数：

```python
chat(user, message)
```

该函数负责接收当前登录用户和用户输入，并返回统一结构：

```json
{
  "reply": "Agent 回复内容",
  "actions": [],
  "trace_id": "本轮对话追踪ID"
}
```

## 3. 整体预约流程

以用户输入为例：

```text
帮我预约下周一下午两点到四点，海淀校区，10个人，做实验
```

整体处理流程如下：

```text
用户输入
  -> /api/agent/chat
  -> chat()
  -> 恢复用户会话
  -> 判断是否为实验室预约相关问题
  -> _extract_form_from_text() 抽取预约字段
  -> _agent_loop() 进入 Agent 主循环
  -> _llm_agent_decide() 调用 DeepSeek 选择工具
  -> _run_tool() 执行业务工具
  -> reservation_service.py 执行业务校验
  -> _llm_compose_tool_reply() 生成自然语言回复
  -> 返回前端展示
```

## 4. 预约表单抽取

Agent 会先把用户自然语言转换为结构化预约表单。相关函数：

```python
_extract_form_from_text(user, text, form, session)
```

该函数会调用多个解析函数：

```python
_detect_date(text)
_detect_time_range(text)
_detect_participant_count(text)
_detect_purpose(text)
_detect_campus(text)
_detect_type(text)
_detect_preference(text)
```

例如：

```text
下周一下午两点到四点，海淀校区，10个人，做实验
```

会被解析成：

```json
{
  "date": "2026-05-04",
  "start_time": "14:00",
  "end_time": "16:00",
  "participant_count": 10,
  "purpose": "课程实验",
  "campus": "海淀校区"
}
```

其中：

- `_detect_date()` 支持今天、明天、后天、下周一、4月25日、2026-04-25 等表达。
- `_detect_time_range()` 支持 14:00-16:00、下午两点到四点、2点半到4点等表达。

## 5. DeepSeek 规划决策

核心函数：

```python
_llm_agent_decide(context, history, form)
```

该函数会把以下信息交给 DeepSeek：

- 当前用户输入
- 当前预约表单
- 已执行过的工具历史
- 可用工具列表
- 预约业务规则
- 当前时间
- 规则引擎初步判断的意图

DeepSeek 输出严格 JSON，例如：

```json
{
  "tool": "recommend_lab",
  "params": {
    "date": "2026-05-04",
    "campus": "海淀校区",
    "participant_count": 10
  },
  "reply": "我先帮你推荐合适的实验室。",
  "done": false
}
```

DeepSeek 不直接执行业务，而是告诉系统下一步应该调用哪个工具。

## 6. 工具体系

Agent 可调用的工具定义在：

```python
AGENT_TOOL_SCHEMAS
```

常用工具包括：

| 工具名 | 作用 |
| --- | --- |
| `query_labs` | 查询实验室列表 |
| `query_schedule` | 查询某天排期 |
| `check_availability` | 检查指定时间段是否可预约 |
| `recommend_lab` | 根据日期、校区、人数等推荐实验室 |
| `recommend_time` | 根据排期推荐可用时间段 |
| `create_reservation` | 创建预约 |
| `my_reservations` | 查询我的预约 |
| `cancel_reservation` | 取消预约 |
| `explain_rules` | 解释预约规则 |

工具执行入口：

```python
_run_tool(tool, params, user, session)
```

该函数负责：

- 检查工具是否存在。
- 检查必填参数是否缺失。
- 缺参数时进入多轮追问。
- 参数完整时调用对应 handler。

工具与处理函数的映射在：

```python
TOOL_HANDLERS
```

例如：

```python
"recommend_lab": _handle_recommend_lab
"recommend_time": _handle_recommend_time
"create_reservation": _handle_create_reservation
```

## 7. 推荐实验室流程

当用户想预约但没有指定实验室 ID 时，Agent 不会要求用户手动输入 ID，而是优先推荐实验室。

核心函数：

```python
_handle_recommend_lab(tool, params, user, session)
```

推荐依据包括：

- 日期
- 校区
- 人数
- 实验室类型
- 上午/下午/晚上偏好
- 实验室容量
- 当天排期空闲情况

推荐逻辑会综合打分：

- 容量是否满足人数
- 容量是否贴近需求
- 当天是否有连续空闲时间
- 是否符合用户偏好的时段
- 是否符合校区和实验室类型

推荐结果会保存到会话中：

```python
session["last_labs"]
```

这样用户后续可以说：

```text
就第一个
```

系统可以知道“第一个”对应哪一个实验室。

## 8. 推荐时间流程

核心函数：

```python
_handle_recommend_time(tool, params, user, session)
```

推荐时间的基础是实验室排期：

```python
get_lab_schedule(lab, target_date)
```

Agent 会计算实验室开放时间内的空闲区间，只把以下状态视为占用：

```python
pending
approved
```

也就是说：

- 待审批预约会占用时间。
- 已通过预约会占用时间。
- 已取消、已驳回预约不会占用时间。

推荐成功后，会把推荐时间保存到：

```python
session["last_recommended_time"]
```

用户后续可以说：

```text
就这个时间
```

系统会继续使用该推荐时间。

## 9. 创建预约流程

最终创建预约的 Agent 工具函数是：

```python
_handle_create_reservation(tool, params, user, session)
```

该函数会组装业务层所需 payload：

```json
{
  "lab_id": 1,
  "campus_id": 1,
  "reservation_date": "2026-05-04",
  "start_time": "14:00",
  "end_time": "16:00",
  "participant_count": 10,
  "purpose": "课程实验"
}
```

然后调用真正的预约业务服务：

```python
create_reservation(user, payload)
```

该函数位于：

```text
backend/app/services/reservation_service.py
```

业务层会进行完整校验：

- 当前用户账户是否正常。
- 实验室是否存在。
- 实验室是否启用。
- 校区与实验室是否匹配。
- 日期是否为过去日期。
- 日期是否超过未来 7 天。
- 开始时间是否早于结束时间。
- 是否至少提前 30 分钟。
- 是否在实验室开放时间内。
- 参与人数是否超过容量。
- 是否与已有预约冲突。
- 是否需要审批。

因此，Agent 即使理解错了用户意图，也不能绕过后端业务规则。

## 10. 多轮对话机制

多轮会话由：

```text
backend/app/services/agent_session.py
```

负责维护。

默认表单结构：

```python
{
  "date": "",
  "start_time": "",
  "end_time": "",
  "participant_count": None,
  "purpose": "",
  "lab_id": None,
  "campus": "",
  "type": "",
  "preference": ""
}
```

会话中还保存：

- `last_labs`：上次推荐的实验室列表。
- `last_reservations`：上次查询到的预约列表。
- `last_recommended_time`：上次推荐的时间。
- `pending_action`：正在等待用户补充信息的动作。
- `followup_context`：追问上下文。

### 10.1 缺参数追问

如果用户只说：

```text
帮我预约实验室
```

系统会发现缺少日期、校区、时间、人数、用途等信息，于是设置：

```python
session["pending_action"]
```

随后用户补充：

```text
下周一下午两点到四点，海淀校区，10个人，做实验
```

会进入：

```python
_continue_pending_action()
```

继续完成之前挂起的预约流程。

### 10.2 承接上文

如果 Agent 推荐了实验室，用户说：

```text
就第一个
```

系统会通过：

```python
_detect_lab_id_or_choice()
```

把“第一个”转换成具体实验室 ID。

如果用户说：

```text
就这个时间
```

系统会从：

```python
session["last_recommended_time"]
```

中恢复推荐时间。

## 11. DeepSeek 回复生成

工具执行完成后，系统并不直接把模板结果返回给用户，而是调用：

```python
_llm_compose_tool_reply()
```

让 DeepSeek 基于真实工具结果生成自然语言回复。

该函数有严格限制：

- 只能使用工具返回的事实。
- 不能编造实验室、时间、状态。
- 不能提到 JSON、工具名、trace_id 等内部实现。
- 回复要简洁，并提示下一步可以怎么做。

例如工具返回：

```text
推荐实验室：计算机实验室A（容量40，校区海淀校区）。推荐理由：容量匹配，下午有空闲。
```

DeepSeek 会整理成更自然的回复：

```text
我建议选择计算机实验室A，位于海淀校区，容量40人，可以满足10人使用。
它在你选择的时间段附近有空闲。
如果你确认使用这个实验室，可以回复“提交预约”。
```

## 12. 降级机制

如果 DeepSeek 不可用，系统会降级到规则引擎：

```python
_fallback_rule_chat()
```

规则引擎通过关键词和正则表达式识别意图，仍可完成基础功能：

- 查询实验室
- 查询排期
- 推荐实验室
- 推荐时间
- 创建预约
- 查询我的预约
- 取消预约

这保证了系统的可用性。

## 13. 答辩可讲亮点

答辩时可以重点说明以下几点：

1. 本系统不是简单关键词问答，而是结合了 DeepSeek 的自然语言理解和后端工具调用。
2. Agent 采用“规划器 + 工具执行器”架构，职责清晰。
3. DeepSeek 不直接操作数据库，所有数据变更必须经过后端服务层校验。
4. 系统支持多轮对话，用户可以分多次补充日期、时间、人数和用途。
5. 系统支持中文自然表达解析，例如“下周一下午两点到四点”。
6. 预约冲突、容量限制、开放时间、提前 30 分钟等规则都在后端统一校验。
7. 工具执行结果会再次交给 DeepSeek 整理，使回复更自然。
8. LLM 不可用时可以降级为规则引擎，保证基础功能可用。

## 14. 示例流程

```text
用户：帮我预约下周一下午两点到四点，海淀校区，10个人，做实验

Agent：
1. 识别日期：下周一
2. 识别时间：14:00-16:00
3. 识别校区：海淀校区
4. 识别人数：10
5. 识别用途：课程实验
6. 发现缺少实验室ID
7. 调用 recommend_lab 推荐实验室
8. 返回推荐结果

用户：就第一个，提交

Agent：
1. 从 last_labs 中找到第一个实验室ID
2. 补全预约表单
3. 调用 create_reservation
4. 后端执行业务校验
5. 创建预约
6. 返回预约成功或等待审批状态
```

## 15. 总结

Agent 模块的核心思想是：

```text
让大模型负责理解，让后端负责执行，让规则保证安全。
```

这种设计既提升了用户体验，又保证了业务系统的可靠性，适合毕业设计中展示“智能化预约管理”的功能亮点。
