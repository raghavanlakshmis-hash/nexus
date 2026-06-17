from langgraph.graph import StateGraph, END
from state.recovery_state import RecoveryState
from agents.intake_agent import run_intake_agent
from agents.care_plan_agent import run_care_plan_agent
from agents.monitoring_agent import run_monitoring_agent, generate_checkin_questions
from agents.escalation_agent import run_escalation_agent
from agents.admin_agent import run_admin_agent

def route_after_monitoring(state: RecoveryState) -> str:
    """Route based on monitoring classification."""
    current = state.get("current_agent", "admin_agent")
    if current == "escalation_agent":
        return "escalation_agent"
    return "admin_agent"

def route_after_intake(state: RecoveryState) -> str:
    """Route after intake — check for PDF failures."""
    if "PDF_PARSE_FAILED" in str(state.get("active_flags", [])):
        return END
    return "care_plan_agent"

def build_intake_graph():
    """Graph for Day 0: intake + care plan generation."""
    workflow = StateGraph(dict)

    workflow.add_node("intake_agent", run_intake_agent)
    workflow.add_node("care_plan_agent", run_care_plan_agent)

    workflow.set_entry_point("intake_agent")
    workflow.add_conditional_edges(
        "intake_agent",
        route_after_intake,
        {
            "care_plan_agent": "care_plan_agent",
            END: END
        }
    )
    workflow.add_edge("care_plan_agent", END)

    return workflow.compile()

def build_monitoring_graph():
    """Graph for daily check-in loop."""
    workflow = StateGraph(dict)

    workflow.add_node("monitoring_agent", lambda state: run_monitoring_agent(
        state, state.get("todays_checkin_responses", {})
    ))
    workflow.add_node("escalation_agent", run_escalation_agent)
    workflow.add_node("admin_agent", run_admin_agent)

    workflow.set_entry_point("monitoring_agent")
    workflow.add_conditional_edges(
        "monitoring_agent",
        route_after_monitoring,
        {
            "escalation_agent": "escalation_agent",
            "admin_agent": "admin_agent"
        }
    )
    workflow.add_edge("escalation_agent", "admin_agent")
    workflow.add_edge("admin_agent", END)

    return workflow.compile()

# Instantiate graphs
intake_graph = build_intake_graph()
monitoring_graph = build_monitoring_graph()