# `agent_service.py` 函数梳理

文件位置：`lab/backend/app/services/agent_service.py`

## 主要函数（主流程）

- `chat(user, message)`（约 1725 行）
  对话总入口，负责消息预处理、会话管理、路由分流和异常兜底。
- `_agent_loop(user, user_input, session, trace_id)`（约 1532 行）
  Agent 主循环，执行“LLM 规划 -> 补参 -> 调工具 -> 再规划”的闭环。
- `_llm_agent_decide(context, history, form)`（约 986 行）
  让 LLM 决定下一步调用哪个工具、参数是什么、是否结束。
- `_run_tool(tool, params, user, session)`（约 1292 行）
  工具执行总入口，统一参数校验并分发到具体业务。
- `_auto_fill_params(...)`（约 1271 行）
  把用户输入和会话表单转成可执行的工具参数。
- `_extract_form_from_text(...)`（约 860 行）
  从自然语言抽取预约字段（日期、时间、人数、用途等）。
- `_fallback_rule_chat(...)`（约 1482 行）
  LLM 异常或不可用时的规则兜底。

## 业务核心函数（工具层）

- `_query_labs(...)`（约 776 行）：查询实验室列表，支持校区/类型/人数/日期过滤。
- `_query_schedule(...)`（约 803 行）：查询某日排期。
- `_recommend_time(...)`（约 819 行）：推荐可用时段，支持上午/下午偏好。
- `_build_date_time_reply(text)`（约 751 行）：回答“今天/明天/后天/下周几/现在几点”。

## 辅助函数分组

### 1) 意图识别与参数抽取
- `_extract_intent`, `_is_lab_related`, `_is_cancel_flow_message`, `_is_date_time_question`
- `_detect_date`, `_detect_time_range`, `_detect_participant_count`, `_detect_purpose`
- `_detect_campus`, `_detect_type`, `_detect_preference`
- `_detect_lab_id_or_choice`, `_detect_reservation_id_or_choice`
- `_llm_extract_form`

### 2) 会话与状态管理
- `_clean_session`, `_save_session`, `_reset_form`

### 3) LLM 与结果封装
- `_call_llm_messages`, `_call_general_llm`, `_safe_json_loads`
- `_normalize_chat_result`, `_tool_call`, `_tool_result`, `_tool_reply_prefer_facts`

### 4) 参数校验与规则
- `_sanitize_tool_params`, `_missing_required_tool_fields`, `_missing_fields_hint`
- `_rules_context`, `_extract_min_advance_days`, `_forbid_duplicate`
- `_normalize_params_shape`, `_safe_int`, `_to_minutes`

### 5) 展示与转跳
- `_labs_to_text`, `_schedule_result_to_text`, `_normalize_nav_path`

### 6) 时间工具
- `_localized_now`, `_now`, `_today`, `_new_trace_id`
- `_relative_day_offset`, `_resolve_relative_date`, `_resolve_date_target`
- `_normalize_clock`

## 快速结论

- 最主要的函数：`chat`、`_agent_loop`、`_llm_agent_decide`、`_run_tool`。
- 业务核心：`_query_labs`、`_query_schedule`、`_recommend_time`、`_extract_form_from_text`。
- 其余函数大多是为主流程服务的辅助层。
