import os
import sys
import warnings

warnings.filterwarnings("ignore")

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient
from strands.types.exceptions import MaxTokensReachedException
from strands.agent.conversation_manager import SlidingWindowConversationManager

from agents.supervisor import create_supervisor
from agents.planner import create_planner_agent
from agents.campaign import create_campaign_agent
from memory.campaign_memory import initialize

# ======================================================================
# MODEL PROVIDER CONFIGURATION
# Uncomment ONE provider block below. Comment out all others.
# ======================================================================

# --- xAI Grok (least restrictive for red team ops) ---
PROVIDER = "xai"
# MODEL_ID = "grok-4-fast-non-reasoning"              # fast, no reasoning ($0.20/$0.50)
# MODEL_ID = "grok-4-0709"                          # full Grok 4 ($3/$15 per M tokens)
# MODEL_ID = "grok-4.20-multi-agent-beta-0309"      # multi-agent beta ($2/$6)
MODEL_ID = "grok-4-fast-reasoning"                   # fast + reasoning ($0.20/$0.50)
# MODEL_ID = "grok-3"                                # Grok 3 ($3/$15)

# --- OpenAI GPT ---
# PROVIDER = "openai"
# MODEL_ID = "gpt-5.4"

# --- Anthropic Claude ---
# PROVIDER = "anthropic"
# MODEL_ID = "claude-sonnet-4-5-20250929"

# ======================================================================

def _build_models(supervisor_max, worker_max):
    """Build supervisor and worker model instances for the active provider."""

    if PROVIDER == "xai":
        from strands.models.openai import OpenAIModel
        key = os.getenv("XAI_API_KEY")
        if not key:
            print("Error: XAI_API_KEY not set. Add it to sec1/.env or export it.")
            sys.exit(1)
        client_args = {"base_url": "https://api.x.ai/v1", "api_key": key}
        sup = OpenAIModel(client_args=client_args, model_id=MODEL_ID, params={"max_completion_tokens": supervisor_max})
        wrk = OpenAIModel(client_args=client_args, model_id=MODEL_ID, params={"max_completion_tokens": worker_max})

    elif PROVIDER == "openai":
        from strands.models.openai import OpenAIModel
        if not os.getenv("OPENAI_API_KEY"):
            print("Error: OPENAI_API_KEY not set. Add it to sec1/.env or export it.")
            sys.exit(1)
        sup = OpenAIModel(model_id=MODEL_ID, params={"max_completion_tokens": supervisor_max})
        wrk = OpenAIModel(model_id=MODEL_ID, params={"max_completion_tokens": worker_max})

    elif PROVIDER == "anthropic":
        from strands.models.anthropic import AnthropicModel
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("Error: ANTHROPIC_API_KEY not set. Add it to sec1/.env or export it.")
            sys.exit(1)
        sup = AnthropicModel(model_id=MODEL_ID, max_tokens=supervisor_max)
        wrk = AnthropicModel(model_id=MODEL_ID, max_tokens=worker_max)

    else:
        print(f"Error: Unknown PROVIDER '{PROVIDER}'. Use 'xai', 'openai', or 'anthropic'.")
        sys.exit(1)

    return sup, wrk


SUPERVISOR_MAX_TOKENS = 300
WORKER_MAX_TOKENS = 3200
WORKER_WINDOW_SIZE = 12
PLANNER_MAX_AGENT_CYCLES = 3
CAMPAIGN_MAX_AGENT_CYCLES = 2


def get_text(result):
    if hasattr(result, "output_text"):
        return result.output_text
    if hasattr(result, "content"):
        try:
            return result.content[0].text
        except Exception:
            pass
    if hasattr(result, "messages"):
        try:
            return result.messages[-1]["content"]
        except Exception:
            pass
    return str(result)


def make_loop_guard(max_cycles):
    state = {"cycles": 0, "request_state": None}

    def _handler(**event):
        if event.get("init_event_loop"):
            request_state = event.get("request_state")
            if isinstance(request_state, dict):
                state["request_state"] = request_state
        if event.get("start_event_loop"):
            state["cycles"] += 1
            if state["cycles"] >= max_cycles and isinstance(
                state["request_state"], dict
            ):
                state["request_state"]["stop_event_loop"] = True

    return _handler


def usage_snapshot(agent):
    usage = getattr(
        getattr(agent, "event_loop_metrics", None), "accumulated_usage", None
    )
    if isinstance(usage, dict):
        return dict(usage)
    return {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}


def usage_delta(before, after):
    keys = (
        set(before.keys())
        | set(after.keys())
        | {"inputTokens", "outputTokens", "totalTokens"}
    )
    return {k: int(after.get(k, 0)) - int(before.get(k, 0)) for k in keys}


def print_usage(label, delta):
    print(
        f"{label} tokens: in={delta.get('inputTokens', 0)} "
        f"out={delta.get('outputTokens', 0)} total={delta.get('totalTokens', 0)}"
    )


def new_worker_conversation_manager():
    return SlidingWindowConversationManager(
        window_size=WORKER_WINDOW_SIZE,
        should_truncate_results=True,
        per_turn=True,
    )


def transport():
    return streamablehttp_client("http://localhost:8001/mcp/")


client = MCPClient(transport)

with client:

    tools = client.list_tools_sync()

    supervisor_model, worker_model = _build_models(SUPERVISOR_MAX_TOKENS, WORKER_MAX_TOKENS)

    supervisor = create_supervisor(supervisor_model)

    print("\nRed Team Agent System Ready (passive / clandestine)")
    print("  Type a goal to begin. Follow-up inputs go to the same agent.")
    print("  Type 'new' to start a fresh task. Type 'exit' to quit.\n")

    # Track active worker so follow-ups go to the same agent
    active_agent = None
    active_label = None
    active_cycles = None

    try:
      while True:

        try:
            if active_agent:
                goal = input(f"{active_label} > ").strip()
            else:
                goal = input("Goal > ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if goal.lower() in ["exit", "quit"]:
            break

        if goal.lower() == "new":
            active_agent = None
            active_label = None
            active_cycles = None
            print("\nSession reset. Enter a new goal.\n")
            continue

        if not goal:
            print("Please enter a goal.")
            continue

        # If no active worker, route through supervisor
        if active_agent is None:
            initialize(goal)

            supervisor_before = usage_snapshot(supervisor)
            decision_result = supervisor(goal)
            supervisor_after = usage_snapshot(supervisor)
            print_usage("Supervisor", usage_delta(supervisor_before, supervisor_after))

            decision_text = get_text(decision_result).lower()
            print("\nSupervisor reasoning:")
            print(decision_text)

            if "campaign" in decision_text or "phishing" in decision_text:
                print("\nRunning Campaign Agent\n")
                active_agent = create_campaign_agent(
                    worker_model,
                    tools,
                    conversation_manager=new_worker_conversation_manager(),
                )
                active_label = "Campaign"
                active_cycles = CAMPAIGN_MAX_AGENT_CYCLES
            else:
                print("\nRunning Planner Agent\n")
                active_agent = create_planner_agent(worker_model, tools)
                active_label = "Planner"
                active_cycles = PLANNER_MAX_AGENT_CYCLES

        # Send goal (or follow-up) to the active worker
        worker_before = usage_snapshot(active_agent)
        try:
            result = active_agent(
                goal, callback_handler=make_loop_guard(active_cycles)
            )
        except MaxTokensReachedException as exc:
            worker_after = usage_snapshot(active_agent)
            delta = usage_delta(worker_before, worker_after)
            recommended_tokens = max(
                WORKER_MAX_TOKENS + 400, delta.get("outputTokens", 0) + 800
            )
            print(f"{active_label} stopped with max_tokens limit.")
            print_usage(active_label, delta)
            print(f"Details: {exc}")
            print(
                f"Tuning hint: increase WORKER_MAX_TOKENS to ~{recommended_tokens} "
                f"(current: {WORKER_MAX_TOKENS}) or lower {active_label} cycles "
                f"(current: {active_cycles})."
            )
            print("\n--------------------------------\n")
            continue
        worker_after = usage_snapshot(active_agent)

        print("\nAgent Response\n")
        print(get_text(result))
        print_usage(active_label, usage_delta(worker_before, worker_after))
        if getattr(result, "stop_reason", None) == "tool_use":
            print(f"\nLoop guard stopped the agent after {active_cycles} cycles.")

        print("\n--------------------------------\n")
    except KeyboardInterrupt:
        pass

    print("\nRed Team client shutting down.\n")
