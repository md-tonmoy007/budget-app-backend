import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from langchain_core.messages import AIMessage

from telegram_bot.src.ai.agent import FinanceAssistant


def test_initialization():
    """Agent constructs without loading tools/graph (both are built lazily/async)."""
    with patch('telegram_bot.src.ai.agent.ChatOpenAI'), \
         patch('telegram_bot.src.ai.agent.MultiServerMCPClient'):
        agent = FinanceAssistant()
        assert agent is not None
        # The langgraph pipeline is built lazily on first message.
        assert agent._graph is None
        assert agent._tool_agent is None


@pytest.mark.asyncio
async def test_process_message_runs_pipeline():
    """process_message builds the analyze->agent graph, runs it for a fresh message,
    and returns the finance agent's final reply text."""
    with patch('telegram_bot.src.ai.agent.ChatOpenAI'), \
         patch('telegram_bot.src.ai.agent.MultiServerMCPClient') as MockClient, \
         patch('telegram_bot.src.ai.agent.create_react_agent') as mock_create_agent:

        # MCP client returns some tools asynchronously.
        MockClient.return_value.get_tools = AsyncMock(return_value=[])

        # The inner tool agent echoes its input then appends its generated reply.
        # _agent_node slices off the inputs, so the final state message is the reply.
        tool_agent = MagicMock()

        async def fake_ainvoke(payload):
            return {"messages": list(payload["messages"]) + [AIMessage(content="Expense logged.")]}

        tool_agent.ainvoke = AsyncMock(side_effect=fake_ainvoke)
        mock_create_agent.return_value = tool_agent

        agent = FinanceAssistant()
        reply = await agent.process_message(12345, "I spent $10 on lunch")

        assert reply == "Expense logged."
        # The finance agent was invoked exactly once for this single-turn message.
        assert tool_agent.ainvoke.await_count == 1


@pytest.mark.asyncio
async def test_analyzer_runs_when_history_exists():
    """On a follow-up turn the analyze node calls the analyzer LLM to summarize
    relevant prior context, and that context is passed to the finance agent."""
    with patch('telegram_bot.src.ai.agent.ChatOpenAI'), \
         patch('telegram_bot.src.ai.agent.MultiServerMCPClient') as MockClient, \
         patch('telegram_bot.src.ai.agent.create_react_agent') as mock_create_agent:

        MockClient.return_value.get_tools = AsyncMock(return_value=[])

        tool_agent = MagicMock()

        async def fake_ainvoke(payload):
            return {"messages": list(payload["messages"]) + [AIMessage(content="Done.")]}

        tool_agent.ainvoke = AsyncMock(side_effect=fake_ainvoke)
        mock_create_agent.return_value = tool_agent

        agent = FinanceAssistant()
        # Force a deterministic analyzer summary.
        agent.analyzer_llm = MagicMock()
        agent.analyzer_llm.ainvoke = AsyncMock(
            return_value=AIMessage(
                content="User is confirming deletion of expense id 5 ($12 lunch)."
            )
        )

        # Turn 1 (fresh) then Turn 2 (follow-up) share the same thread id.
        await agent.process_message(999, "delete my lunch expense")
        await agent.process_message(999, "yes")

        # Analyzer ran on the second turn (history now exists).
        assert agent.analyzer_llm.ainvoke.await_count == 1
        # The finance agent received the summary as a leading context message.
        last_payload = tool_agent.ainvoke.call_args_list[-1].args[0]
        joined = " ".join(
            m.content for m in last_payload["messages"] if isinstance(m.content, str)
        )
        assert "expense id 5" in joined
