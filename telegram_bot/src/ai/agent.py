import logging
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    trim_messages,
)
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from ..config.config import Config

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

# How many of the most recent conversation messages the analyzer looks back over.
HISTORY_WINDOW = 10

# Sentinel the analyzer returns when no earlier message is relevant.
NO_CONTEXT = "NO_RELEVANT_CONTEXT"

FALLBACK_ANALYZER_PROMPT = (
    "You analyze a finance chatbot conversation. Given the latest user message and the "
    "earlier conversation, decide which earlier messages are relevant to the latest message "
    "and write a concise but COMPLETE summary of only that relevant context (accounts, amounts, "
    "dates, record ids, the action under discussion, and any pending confirmation the user may "
    f"now be answering). If nothing earlier is relevant, reply exactly: {NO_CONTEXT}"
)


class AssistantState(TypedDict):
    """Shared graph state.

    ``messages`` is the full per-chat history (persisted by the checkpointer);
    ``context_summary`` is produced by the analyze node and consumed by the agent node.
    """

    messages: Annotated[list, add_messages]
    context_summary: str


def _render(messages) -> str:
    """Render prior messages as a compact transcript for the analyzer LLM."""
    lines = []
    for m in messages:
        if isinstance(m, HumanMessage):
            role = "User"
        elif isinstance(m, AIMessage):
            role = "Assistant"
        elif isinstance(m, ToolMessage):
            role = f"ToolResult({getattr(m, 'name', '?')})"
        else:
            role = m.__class__.__name__
        content = m.content if isinstance(m.content, str) else str(m.content)
        # Note any tool calls the assistant made so the analyzer keeps that detail.
        tool_calls = getattr(m, "tool_calls", None)
        if tool_calls:
            names = ", ".join(tc.get("name", "?") for tc in tool_calls)
            content = (content + f" [called tools: {names}]").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


class FinanceAssistant:
    """Two-stage tool-calling finance assistant.

    Stage 1 (analyze): a lightweight LLM reads the last ~10 messages of the chat,
    decides which are relevant to the new message, and distills them into a complete
    summary. Stage 2 (agent): the tool-calling finance agent receives only the new
    message plus that summary as context, then calls MCP tools to do the work.

    A langgraph checkpointer keeps the full per-chat history (keyed by Telegram chat
    id) so the analyzer always has the real conversation to draw on, while the finance
    agent stays focused on distilled, relevant context.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model=Config.OPENROUTER_MODEL,
            api_key=Config.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
            default_headers={
                "HTTP-Referer": "https://github.com/budget-planner-bot",
                "X-Title": "Budget Planner Bot",
            },
        )
        # Separate, tool-free model instance for the analysis/summarization stage.
        self.analyzer_llm = ChatOpenAI(
            model=Config.OPENROUTER_MODEL,
            api_key=Config.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
            default_headers={
                "HTTP-Referer": "https://github.com/budget-planner-bot",
                "X-Title": "Budget Planner Bot",
            },
        )
        self.mcp_client = MultiServerMCPClient(
            {
                "budget-planner": {
                    "url": Config.MCP_SERVER_URL,
                    "transport": "streamable_http",
                }
            }
        )
        self.system_prompt = self._load_prompt("system.txt", "You are a helpful finance assistant. Use the available tools to help the user.")
        self.analyzer_prompt = self._load_prompt("analyzer.txt", FALLBACK_ANALYZER_PROMPT)
        self._graph = None       # compiled langgraph pipeline (built lazily)
        self._tool_agent = None  # inner react agent (built lazily, tool loading is async)

    def _load_prompt(self, filename: str, fallback: str) -> str:
        try:
            return (PROMPTS_DIR / filename).read_text()
        except FileNotFoundError:
            logger.warning("%s not found; using fallback prompt", filename)
            return fallback

    # ------------------------------------------------------------------ nodes

    async def _analyze_node(self, state: AssistantState) -> dict:
        """Stage 1: pick the relevant prior messages and summarize them."""
        history = state["messages"]
        current = history[-1]
        # Look back over the last HISTORY_WINDOW messages, excluding the current one.
        try:
            window = trim_messages(
                history,
                strategy="last",
                token_counter=len,
                max_tokens=HISTORY_WINDOW,
                start_on="human",
                include_system=False,
            )
        except Exception:
            window = history[-HISTORY_WINDOW:]
        prior = window[:-1]  # everything in the window except the current message

        if not prior:
            logger.info("[analyze] no prior history; skipping summary")
            return {"context_summary": ""}

        transcript = _render(prior)
        current_text = current.content if isinstance(current.content, str) else str(current.content)
        try:
            resp = await self.analyzer_llm.ainvoke(
                [
                    SystemMessage(content=self.analyzer_prompt),
                    HumanMessage(
                        content=(
                            f"Latest user message:\n{current_text}\n\n"
                            f"Earlier conversation (oldest first):\n{transcript}"
                        )
                    ),
                ]
            )
            summary = resp.content if isinstance(resp.content, str) else str(resp.content)
        except Exception as e:
            logger.error("[analyze] summarization failed: %s", e, exc_info=True)
            return {"context_summary": ""}

        if NO_CONTEXT in summary:
            logger.info("[analyze] no relevant prior context")
            return {"context_summary": ""}
        logger.info("[analyze] relevant context summary: %s", summary)
        return {"context_summary": summary}

    async def _agent_node(self, state: AssistantState) -> dict:
        """Stage 2: run the tool-calling finance agent on the current message + summary."""
        current = state["messages"][-1]
        summary = (state.get("context_summary") or "").strip()

        agent_input = []
        if summary:
            agent_input.append(
                SystemMessage(
                    content=(
                        "Relevant context from earlier in this conversation (use only what "
                        f"pertains to the current request):\n{summary}"
                    )
                )
            )
        agent_input.append(current)

        # MCP tools are exposed as async StructuredTools, so the inner agent must
        # use its async execution path. Calling invoke() here makes ToolNode try
        # to execute those tools synchronously and raises NotImplementedError.
        result = await self._tool_agent.ainvoke({"messages": agent_input})
        # The inner agent returns our input messages followed by the ones it generated.
        # Persist only the generated outputs (the current human is already in state).
        generated = result["messages"][len(agent_input):]
        return {"messages": generated}

    # --------------------------------------------------------------- assembly

    async def _ensure_graph(self):
        """Build the inner tool agent and the analyze->agent pipeline once."""
        if self._graph is None:
            tools = await self.mcp_client.get_tools()
            logger.info("Loaded %d MCP tools from the budget-planner server", len(tools))
            # Inner agent has no checkpointer: the parent graph owns persistence, and
            # each turn we hand it exactly the context it needs (current msg + summary).
            self._tool_agent = create_react_agent(self.llm, tools, prompt=self.system_prompt)

            builder = StateGraph(AssistantState)
            builder.add_node("analyze", self._analyze_node)
            builder.add_node("agent", self._agent_node)
            builder.add_edge(START, "analyze")
            builder.add_edge("analyze", "agent")
            builder.add_edge("agent", END)
            self._graph = builder.compile(checkpointer=MemorySaver())
        return self._graph

    # ------------------------------------------------------------------ logging

    @staticmethod
    def _log_trace(chat_id, messages):
        """Log the agent's tool calls and their results for this turn."""
        for msg in messages:
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                for tc in tool_calls:
                    logger.info(
                        "[chat %s] -> tool call: %s args=%s",
                        chat_id, tc.get("name"), tc.get("args"),
                    )
            if isinstance(msg, ToolMessage):
                content = getattr(msg, "content", "")
                if isinstance(content, str) and len(content) > 500:
                    content = content[:500] + "...(truncated)"
                logger.info(
                    "[chat %s] <- tool result (%s): %s",
                    chat_id, getattr(msg, "name", "?"), content,
                )

    # ------------------------------------------------------------------ entry

    async def process_message(self, chat_id, user_message: str) -> str:
        """Process a user message via the analyze->agent pipeline and return the reply."""
        try:
            graph = await self._ensure_graph()
            logger.info("[chat %s] processing message: %r", chat_id, user_message)
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=user_message)]},
                config={"configurable": {"thread_id": str(chat_id)}},
            )
            messages = result.get("messages", [])
            self._log_trace(chat_id, messages)
            if not messages:
                return "I'm not sure how to respond to that."
            reply = messages[-1].content
            # Some models return content as a list of parts; normalize to text.
            if isinstance(reply, list):
                reply = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in reply
                )
            return reply or "Done."
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return "I encountered an error processing your request."
