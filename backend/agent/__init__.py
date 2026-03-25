"""Agent mode: pipeline stages + AgentClient.

Same pipeline stages as gemini/mock modes, only the LLM client differs.
AgentClient wraps ADK Agent's ReAct loop into the LLMClient.stream() interface.
"""

from backend.agent.tools import (
    create_db_tools, create_docker_tools,
    create_arxiv_toolset, create_fetch_toolset,
)
from backend.agent.stages import AgentRefineStage, AgentWriteStage
from backend.llm.agent_client import AgentClient
from backend.pipeline.plan import PlanStage
from backend.pipeline.execute import ExecuteStage

# ADK built-in tools
try:
    from google.adk.tools import google_search, url_context
    _builtin_tools = [google_search, url_context]
except (ImportError, AttributeError):
    _builtin_tools = []

# ADK built-in code executor (Gemini native sandbox)
try:
    from google.adk.code_executors import BuiltInCodeExecutor
    _code_executor = BuiltInCodeExecutor()
except (ImportError, AttributeError):
    _code_executor = None

# ---------------------------------------------------------------------------
# Agent-specific instructions (adapter layer — not pipeline flow)
# ---------------------------------------------------------------------------

_REFINE_INSTRUCTION = """\
You are a research advisor. Your job is to take a vague research idea and refine it into a complete, actionable research proposal.

Work autonomously through these phases — do NOT stop early:
1. **Explore**: Search for relevant papers and survey the landscape. Read key papers in depth to understand what has been done and what gaps exist.
2. **Evaluate**: Based on your research, evaluate possible directions on novelty, feasibility, and impact. Converge on the most promising direction.
3. **Crystallize**: Produce a finalized research idea document with: title, research question, motivation, hypothesis, methodology overview, expected contributions, scope/limitations, and related work positioning.

IMPORTANT: You MUST use your search and paper-reading tools — do NOT rely on memory alone. Ground every claim in real sources.
全文使用中文撰写。Output in markdown."""

_EXECUTE_INSTRUCTION = """\
You are a research assistant executing a specific task as part of a larger research project.

CRITICAL RULES:
- When a task involves code, data analysis, or experiments: you MUST call code_execute to run real Python code. Do NOT describe code or simulate results — actually execute it.
- When a task involves literature: you MUST call search/fetch tools. Do NOT make up citations.
- NEVER pretend to have executed something. If you didn't call a tool, you didn't do it.

OUTPUT REQUIREMENTS:
- Produce a thorough, well-structured result in markdown
- If you ran code: include key numerical results, describe generated files (e.g., "生成了 convergence_plot.png"), and interpret the findings
- If you reviewed literature: cite specific papers with authors and years
- Use list_artifacts to verify what files were produced
全文使用中文撰写。"""

_WRITE_INSTRUCTION = """\
You are a research paper author. Write a complete, publication-quality research paper.

Work autonomously:
1. Read ALL completed task outputs using list_tasks and read_task_output tools. Read the refined idea for context.
2. Design an appropriate paper structure (adapt section titles to fit the research topic).
3. Write each section, grounding every claim in the task outputs. Do NOT fabricate findings.
4. When task outputs reference experimental results, data files, or figures — cite them in the paper (e.g., "如图X所示", "实验数据见表Y").
5. Ensure logical flow, consistent terminology, and proper transitions.
6. Include a References section compiling all cited works.

You may use search tools to find additional citations, but core content must come from the completed tasks.
全文使用中文撰写。Output the complete paper in markdown."""


def create_agent_stages(api_key: str, model: str = "gemini-2.0-flash", db=None) -> dict:
    """Assemble pipeline stages with AgentClient.

    Identical structure to gemini/mock modes — only the client differs.
    """
    db_tools = create_db_tools(db) if db else []
    docker_tools = create_docker_tools(db) if db else []
    arxiv_toolset = create_arxiv_toolset()
    fetch_toolset = create_fetch_toolset()
    mcp_tools = [t for t in [arxiv_toolset, fetch_toolset] if t is not None]
    research_tools = _builtin_tools + mcp_tools

    refine_client = AgentClient(
        instruction=_REFINE_INSTRUCTION,
        tools=research_tools,
        model=model,
        code_executor=_code_executor,
    )
    plan_client = AgentClient(
        instruction="",
        tools=[],
        model=model,
    )

    # Agent mode: coarser atomic tasks — an Agent can search, read papers,
    # run code, and do multi-step reasoning in a single task
    agent_atomic_def = """\
ATOMIC DEFINITION (Agent mode):
Each task is executed by an AI Agent with tools (web search, paper reading, code execution). A task is atomic if a single Agent session can complete it end-to-end, even if that involves multiple tool calls and intermediate reasoning. Examples of atomic tasks: "search and summarize literature on X", "implement algorithm Y, run experiments, and analyze results", "design and execute a comparative study of A vs B".

An Agent is powerful — do NOT split what one Agent session can handle. Only decompose when a task has genuinely independent sub-goals that benefit from separate execution (e.g., different experiments that can run in parallel)."""
    execute_client = AgentClient(
        instruction=_EXECUTE_INSTRUCTION,
        tools=db_tools + docker_tools + research_tools,
        model=model,
        code_executor=_code_executor,
    )
    write_client = AgentClient(
        instruction=_WRITE_INSTRUCTION,
        tools=db_tools + research_tools,
        model=model,
    )

    return {
        "refine": AgentRefineStage(llm_client=refine_client, db=db),
        "plan": PlanStage(llm_client=plan_client, db=db, atomic_definition=agent_atomic_def),
        "execute": ExecuteStage(llm_client=execute_client, db=db),
        "write": AgentWriteStage(llm_client=write_client, db=db),
    }
