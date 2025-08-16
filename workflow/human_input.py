"""
Agent which demonstrates Human Input tool
"""

import asyncio

from mcp_agent.core.fastagent import FastAgent

# 创建 FastAgent 应用实例，用于定义和管理 Agent
fast = FastAgent("Human Input")


# 定义 Agent 并启用人类输入功能
@fast.agent(
    instruction="一个协助完成基本任务的 AI Agent，在需要时请求人类输入。",  # Agent 的指令说明
    human_input=True,  # 启用人类输入工具，允许 Agent 在需要时向用户请求输入
)
async def main() -> None:
    # 运行 Agent 并进入上下文管理器
    async with fast.run() as agent:
        # 这通常会触发 LLM 请求人类输入工具，因为需要更多信息来确定序列的下一个数字
        await agent("print the next number in the sequence")
        # 显示默认提示符 "STOP"，等待用户输入
        await agent.prompt(default_prompt="STOP")


# 程序入口点，运行异步主函数
if __name__ == "__main__":
    asyncio.run(main())
