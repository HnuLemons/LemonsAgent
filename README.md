# LemonsAgent

从零实现的最小可用AI Agent--LemonsAgent


## 能力一览

- 四步对话循环（输入 → 模型判断 → 工具调用 → 继续/返回），**流式输出**
- 工具系统：5 个内置工具（shell 命令、Tavily 搜索、天气、计算器、技能加载）
- 技能系统：SKILL.md 仓库扫描与按需加载
- 上下文管理：轮次限制、滑动窗口、基础压缩 + LLM 压缩双层机制
- 记忆系统：长期记忆 / 用户档案 / 情景记忆 / 原始对话记录
- 多会话管理：会话隔离、持久化、随时切换续聊
- 可观测性：工具调用 trace（内存 + JSONL 日志）
- 43 个单元测试全覆盖

## 项目结构

```
lemons_agents/
├── .env                     # 大模型配置
├── agent.py                 # 主启动入口
├── core/                    # 核心框架层
│   ├── config.py            # 配置管理
│   ├── loop.py              # 内层循环 + 系统提示词组装
│   ├── runner.py            # 外层循环
│   ├── context.py           # 上下文管理
│   ├── session.py           # 会话管理
│   ├── memory.py            # 记忆存储
│   ├── compactor.py         # LLM 压缩
│   ├── skill.py             # 技能加载器
│   ├── exceptions.py        # 统一异常体系
│   └── __init__.py          # 包级便捷导出
├── tools/                   # 工具系统层
│   ├── base.py              # BaseTool 抽象基类
│   ├── registry.py          # 工具注册表 + 统一执行入口（含 trace）
│   ├── trace.py             # 工具调用日志
│   ├── chain.py             # 工具链编排（待开发）
│   ├── async_executor.py    # 异步执行器（待开发）
│   └── builtin/             # 内置工具实现
├── tests/                   # 单元测试（unittest，43 用例）
├── Skill/                   # 技能仓库（SKILL.md）
├── templates/               # 提示词资产
│   ├── SOUL.md              # 人设
│   ├── USER.md              # 用户档案
│   └── agent/compact_prompt.md  # LLM 压缩提示词
├── memory/                  # 记忆数据
│   ├── MEMORY.md            # 长期记忆
│   ├── history.jsonl        # 原始对话记录
│   └── Contextual memory/   # 情景记忆（YYYY-MM-DD.md）
├── sessions/                # 会话存档
└── logs/tool_trace.jsonl    # 工具调用日志
```

## 系统设计

### 四步循环

```
┌─ runner.py（外层循环，多轮对话）──────────────────────────┐
│  Step 1  接收用户输入 → 写入上下文                        │
│           ↓ agent_turn()                              │
│  ┌─ loop.py（内层循环，单轮"模型↔工具"）──────────────┐   │
│  │  Step 2  模型判断：直接回复 or 调用工具            │    │
│  │     （判断由模型做出，代码只读 stop_reason）       │    │
│  │  Step 3  调用工具，收集结果                      │    │
│  │  Step 4  结果写回上下文 ──→ 回到 Step 2          │    │
│  │           或模型不再调工具 ──→ 流式返回给用户      │    │
│  └───────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────┘
```

### 上下文管理（双层压缩）

| 层 | 触发时机 | 做什么 | 产物 |
|---|---|---|---|
| 基础压缩（context.py） | 每次发模型前，超阈值即触发（本地零成本） | 超长工具结果截断；超 20 轮/40 条从头部滑动丢弃，并对齐 tool_use/tool_result 配对边界 | 无（直接裁剪） |
| LLM 压缩（compactor.py） | 每轮结束检查，历史 > 18 条触发（调模型有成本） | 旧消息发给"记忆整理员"，产出摘要 | 情景记忆段落 + 新版 MEMORY.md / USER.md，上下文只留最近 10 条 |

### 记忆系统：召回时机与放置方式

#### 总览：四类记忆

| 记忆 | 存放位置 | 写入时机 | 召回时机 |
|---|---|---|---|
| 长期记忆 | `memory/MEMORY.md` | LLM 压缩时由模型**整体改写** | 每次调用模型前，**全文**注入系统提示词【长期记忆】区块 |
| 用户档案 | `templates/USER.md` | LLM 压缩检测到明确偏好信号时才更新（否则原样保留） | 每次调用模型前，**全文**注入【用户画像】区块 |
| 情景记忆 | `memory/Contextual memory/YYYY-MM-DD.md`（按日期一个文件） | LLM 压缩时向**当天文件**追加一个带时间戳的段落 | 每次调用模型前，**只读取当天日期的文件**注入【今日情景记忆】区块 |
| 原始对话 | `memory/history.jsonl` | 每条消息产生时追加（只增不改） | **不召回**。仅作原始档案备查 |

#### 召回路径：每次模型调用前现组装

`core/loop.py` 的 `build_system_prompt()` 在**每一次**模型调用前重新执行
（包括同一轮内工具调用后的再次调用），组装顺序：

```
① SOUL.md（人设，loop.py _load_soul() 读取，缺失回退默认人设）
② 固定行为指令（"遇到不熟悉的专题先调用 load_skill..."）
③ 【长期记忆】   MEMORY.read_memory()         → memory/MEMORY.md 全文
④ 【用户画像】   MEMORY.read_user()           → templates/USER.md 全文
⑤ 【今日情景记忆】MEMORY.read_today_episode() → Contextual memory/<今天>.md
⑥ 当前可用技能列表（Skill/ 目录实时扫描的描述）
= system 参数，与 messages（会话上下文）一起发给模型
```


#### 写入路径：LLM 压缩的完整流程

触发条件（`core/compactor.py` 的 `compact_history`，每轮对话结束时检查）：

```python
if len(history) <= COMPACT_AFTER_MESSAGES:  # 默认 18 条
    return history                           # 未超阈值：原样返回，什么都不发生
old_messages = history[:-RECENT_MESSAGES]    # 最旧的 N 条（留出最近 10 条）
```

触发后，旧消息文本 + 当前 MEMORY.md + 当前 USER.md + 今日已有情景记忆，
填入 `templates/agent/compact_prompt.md` 模版发给模型，要求返回三段 XML：

| 返回段落 | 处理方式 | 落点 |
|---|---|---|
| `<episode>` | **追加**到当天情景记忆文件（`## HH:MM 小标题` 段落） | `Contextual memory/YYYY-MM-DD.md` |
| `<updated_memory>` | **整体覆盖**长期记忆（模型负责保留有效旧条目 + 合并新事实） | `memory/MEMORY.md` |
| `<updated_user>` | **整体覆盖**用户档案（仅当旧对话中有明确偏好信号才变化） | `templates/USER.md` |

最后上下文被裁剪为最近 10 条（`context.replace(compacted)`）——
被裁掉的旧消息已以摘要形式沉淀进记忆文件，信息不丢失。
压缩失败（API 异常等）则保留完整 history，不丢数据。

#### 与会话上下文的关系（两套"历史"不要混淆）

| | 会话上下文 | 记忆文件 |
|---|---|---|
| 存放 | `sessions/<id>.json`（每会话独立） | `memory/` + `templates/USER.md`（全局共享） |
| 内容 | 发给模型的 messages 列表（完整消息，含工具配对） | 摘要性知识（目标/事实/偏好/情景段落） |
| 管理者 | `ContextManager`（窗口裁剪：轮次/条数/截断） | `MemoryStore`（读写降级保护） |
| 召回方式 | 作为 `messages=` 参数整体发送 | 经 `build_system_prompt` 注入 `system=` 参数 |
| 隔离性 | **会话间隔离**（窗口1看不到窗口2） | **跨会话共享**（窗口1记住的事窗口2也知道，有意设计） |

衔接点：LLM 压缩把"上下文里放不下的旧消息"转化为"记忆文件里的摘要"，
记忆文件又通过系统提示词回到每一次模型调用中——形成闭环。

#### 代码索引

| 职责 | 位置 |
|---|---|
| 提示词组装（召回入口） | `core/loop.py` → `build_system_prompt()` |
| 人设读取 | `core/loop.py` → `_load_soul()` |
| 记忆读写 / 降级 | `core/memory.py` → `MemoryStore` |
| LLM 压缩 | `core/compactor.py` → `compact_history()` |
| 压缩提示词模版 | `templates/agent/compact_prompt.md` |
| 压缩阈值配置 | `core/config.py` → `COMPACT_AFTER_MESSAGES` / `RECENT_MESSAGES` |

### 异常处理原则

- **关键路径快速失败**：缺 API Key / .env → 启动即抛 `ConfigError` 并给配置指引
- **附属能力优雅降级**：记忆读写、技能加载、会话保存、日志写入失败 → 告警后继续，绝不中断对话
- **工具失败自我表达**：工具内部错误转为 `"Error: "` 前缀字符串返回给模型，模型可据此自愈

## 运行方式

### 1. 安装依赖

```bash
pip install anthropic python-dotenv pyyaml
```

### 2. 配置 lemons_agents/.env

```bash
ANTHROPIC_API_KEY=你的密钥
ANTHROPIC_BASE_URL=https://api.anthropic.com   # 或兼容端点
ANTHROPIC_MODEL=模型名
TAVILY_API_KEY=Tavily密钥                        # https://app.tavily.com 免费申请
```

可选环境变量（均有默认值）：

| 变量 | 默认 | 说明 |
|---|---|---|
| `AGENT_MAX_TURNS` | 20 | 上下文最大对话轮次 |
| `AGENT_CONTEXT_MAX_MESSAGES` | 40 | 上下文最大消息条数 |
| `AGENT_TOOL_RESULT_MAX_CHARS` | 2000 | 单条工具结果截断阈值 |
| `AGENT_MEMORY_COMPACT_AFTER` | 18 | 触发 LLM 压缩的历史消息数 |
| `AGENT_SOUL_FILE` | `SOUL.md` | 人设文件名（templates/ 下，见下节） |

### 2.1 人设切换（只需改一步配置）

Agent 的人设由 `templates/` 下的 Markdown 文件定义，**默认指向 `SOUL.md`（通用模版）**。
每次调用模型前，`core/loop.py` 的 `build_system_prompt()` 会读取该文件注入系统提示词。

**切换人物只改一行配置**，无需动代码：

```bash
# lemons_agents/.env
AGENT_SOUL_FILE=SOUL_zhenmei.md   # 改成 templates/ 下任意人设文件名
```

**新增自定义人物**：

1. 复制 `templates/SOUL.md` 为 `templates/SOUL_<名字>.md`（如 `SOUL_zhenmei.md`）
2. 按模版里的注释填写身份 / 性格 / 沟通方式
3. `.env` 中把 `AGENT_SOUL_FILE` 指向新文件名

约定：`SOUL_*.md` 已在 `.gitignore` 中（私人设定不入库），
只有通用模版 `SOUL.md` 会提交；人设文件缺失时 Agent 回退到极简默认人设并告警，不会崩溃。

### 3. 启动

```bash
python -m lemons_agents.agent        # 方式一：包模式（推荐）
python lemons_agents/agent.py        # 方式二：直接运行脚本
```

### 4. REPL 斜杠命令

```
/new          创建新会话
/list         列出所有会话
/switch <id>  切换会话（支持 id 前缀）
/trace [n]    查看最近 n 条工具调用记录
/help         帮助
/exit         退出（或 Ctrl+D / Ctrl+C）
```

### 5. 运行测试

```bash
python -m unittest discover -s lemons_agents/tests -t .
```






