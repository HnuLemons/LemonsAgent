
# LemonsAgent设计问题记录表
# 1️⃣.env配置无法生效
## 问题描述：
注意到每次配置.env中key、url等配置项时，尽管保存后重启服务依旧无法生效。
## 排查思路：
1.首先确认API key是否失效
2.然后确认.env文件是否存在多余空格等格式错误
3.检查环境变量，echo ANTHROPIC_API_KEY
4.最终发现环境变量ANTHROPIC_API_KEY已有旧值，而旧值已经过期
## 解决方案：
1. 为环境变量ANTHROPIC_API_KEY赋新值，但这意味着要同时为ANTHROPIC_BASE_URL和ANTHROPIC_MODEL也赋新值，环境变量只有一份，之后如果需要修改API则又需要改环境变量，非常麻烦，而且无法实现两个程序使用两份不同的大模型配置
2. 在加载.env大模型配置时覆盖环境变量即可，为.env设置更高的优先级
```
    # override=True：项目 .env 优先于 shell 环境变量，
    # 防止 shell 里残留的同名旧值（如旧 TAVILY_API_KEY）悄悄覆盖项目配置
    load_dotenv(ENV_PATH, override=True)  # 加载环境变量
```
# 2️⃣超长工具结果原样发送，挤占上下文
## 问题描述：
run_command 执行 ls -R、web_search 返回多页结果时，单条工具结果可能上千行。若原样写入上下文，不仅每次模型调用都要重复发送，还容易把整个会话上下文撑爆。
## 排查思路：
① 复现一次大输出工具调用，观察 logs/tool_trace.jsonl 中 result 字段长度；
② 确认该结果被完整写入 context.messages 并在后续每轮重复发送；
③ 估算其对上下文 token 的占用比例。
## 解决方案：
在 core/context.py 的 _truncate_tool_results() 方法中对超长工具结果保留头尾各一半、中间标注省略字符数，阈值由 AGENT_TOOL_RESULT_MAX_CHARS（默认 2000）控制，写入前就地截断。既保留关键信息，又控制单条体积。
# 3️⃣记忆文件/目录不存在时，首次读写直接崩溃
## 问题描述：
首次运行或记忆目录被清理后，memory/MEMORY.md、templates/USER.md、Contextual memory/ 等不存在，read_text() / open() 抛 FileNotFoundError，导致提示词组装失败、Agent 无法启动。
# 解决思路：
在 core/memory.py 的 ensure_files() 中集中创建缺失目录与初始文件（MEMORY.md、USER.md 写入空标题，history.jsonl touch），所有读写方法调用前先 ensure_files()，返回 False 则跳过。首次运行自动初始化，无需手动建文件。
# 4️⃣工具内部抛异常时，Agent 整体崩溃而非让模型自愈
## 问题描述
工具执行（如 calculator 收到非法表达式、weather 网络异常）抛异常时，若不捕获会冒泡到 agent_turn的 while 循环，导致 Agent 直接退出，用户需重启。
## 排查思路
① 让 calculator计算 “1/0” 这样的非法表达式，观察是否崩溃退出；
② 确认异常未被 execute_tool 捕获；
③ 对照"工具失败自我表达"设计原则，确认工具错误应转为字符串返回。
## 解决方案
execute_tool()包裹 run(block.input)，把任意异常转为 “Error: tool '...' 执行失败: {exc}” 字符串返回，并仍记入 trace。模型收到带 Error前缀的结果可自行判断并重试/换方案，Agent 主流程不受影响。