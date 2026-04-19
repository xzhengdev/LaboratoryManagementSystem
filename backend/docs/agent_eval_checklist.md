# Agent 评测用例清单

适用文件：`lab/backend/app/services/agent_service.py`

## 1. 路由与意图识别

| ID | 用户输入 | 期望工具链 | 断言 |
|---|---|---|---|
| R-01 | 帮我找明天可用实验室 | `query_labs` | 走 `agent_loop` |
| R-02 | 给我推荐明天下午可用时间 | `recommend_time` | `preference=下午` |
| R-03 | 下午2点开始 | 续接上一轮任务 | `lab_followup=True` |
| R-04 | 今天天气怎么样 | 无工具 | 走 `general_llm` |

## 2. 日期时间解析

| ID | 用户输入 | 期望参数 | 断言 |
|---|---|---|---|
| D-01 | 明天有哪些实验室 | `date=2026-04-20` | 相对日期正确 |
| D-02 | 后天上午可用时间 | `date=2026-04-21`,`preference=上午` | 解析正确 |
| D-03 | 4月22日可以预约吗 | `date=2026-04-22` | 月日解析正确 |

## 3. 查询与推荐工具

| ID | 用户输入 | 期望工具 | 断言 |
|---|---|---|---|
| Q-01 | 查询明天实验室 | `query_labs` | 返回列表 |
| Q-02 | 查询明天共享基础虚拟仿真实验室排期 | `query_schedule` | `lab_id` 生效 |
| Q-03 | 推荐明天下午时间 | `recommend_time` | 不得返回上午时段 |
| Q-04 | 推荐一个明天实验室 | `recommend_lab` | 返回数字 `lab_id` |

## 4. 预约生命周期

| ID | 用户输入 | 期望工具链 | 断言 |
|---|---|---|---|
| B-01 | 帮我预约明天14:00-16:00 共享基础虚拟仿真实验室 20人 用途:课程实验 | `create_reservation` | 创建成功 |
| B-02 | 取消预约123 | `cancel_reservation` | 状态更新 |
| B-03 | 查看我的预约 | `my_reservations` | 返回列表 |

## 5. 多步规划与容错

| ID | 场景 | 期望行为 | 断言 |
|---|---|---|---|
| L-01 | `recommend_lab` -> `recommend_time` | 两步链路 | 第2步使用回填的真实 `lab_id` |
| L-02 | 工具成功后再规划 | 可继续或结束 | 不出现无意义缺参步骤 |
| L-03 | LLM不可用 | 规则降级 | 走 `_fallback_rule_chat` |

## 6. 日志验证

| ID | 期望日志事件 | 断言 |
|---|---|---|
| T-01 | `chat_received` | 收到用户输入 |
| T-02 | `route` | 路由分支正确 |
| T-03 | `llm_decision` | 显示 `step/tool/done` |
| T-04 | `auto_fill_params` | 补参结果可见 |
| T-05 | `tool_executed` | 工具结果摘要可见 |
| T-06 | `form_synced_by_tool` | 推荐后回填真实 `lab_id` |

## 建议执行顺序

1. 先跑 R + D?路由和时间解析基线）
2. 再跑 Q + L?工具链路和多步规划）
3. 最后跑 B + T?业务高风险路径和可观测性）
