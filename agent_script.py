"""
agent_script.py

PRD vs Jira Drift Detector
Compares a Confluence PRD to its linked Jira epic using Mistral's
Atlassian connector, classifies each requirement as MATCHES, 
CONFIRMED_CHANGE, or SILENT_DRIFT, and can generate either structured 
JSON output or a full HTML dashboard.
"""

import os
import json
from mistralai.client import Mistral

# --- Setup ---
client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

ATLASSIAN_CONNECTOR_ID = "0198e70f-57b0-77f6-a752-0a7f5ea2da35"  # your connector ID
AGENT_ID = None  # set after first run of create_agent(), then hardcode it here to skip recreating


AGENT_INSTRUCTIONS = (
    "You compare Confluence PRDs to their linked Jira epics and flag where "
    "scope has silently diverged without a corresponding change record. "
    "Only classify a mismatch as CONFIRMED_CHANGE if you find explicit evidence: "
    "a comment referencing the PRD or a stakeholder decision, an edit to the PRD "
    "itself around the same time, or a linked discussion. A comment that merely "
    "explains an implementation choice without referencing an agreed scope change "
    "does NOT count as confirmed — default to SILENT_DRIFT if evidence is ambiguous. "
    "Also flag any PRD requirement that has no corresponding Jira story at all, "
    "even if not explicitly contradicted — treat unassigned requirements as their "
    "own SILENT_DRIFT case. "
    "Only compare requirements explicitly stated in the PRD. Do not invent "
    "additional requirements or speculate about unstated goals. "
    "\n\n"
    "When asked for a comparison as data, respond ONLY with a JSON array, no "
    "other text, in this exact format: "
    '[{"requirement": "...", "jira_story": "...", "classification": '
    '"MATCHES" | "CONFIRMED_CHANGE" | "SILENT_DRIFT", "reason": "...", '
    '"likely_cause": "..."}]'
    "\n\n"
    "When asked to produce a dashboard or HTML report, generate a single "
    "self-contained HTML file (vanilla JS only, no external libraries) that: "
    "shows one card per requirement with its classification, reason, and "
    "likely cause; color-codes cards by classification (green for MATCHES, "
    "amber for CONFIRMED_CHANGE, red for SILENT_DRIFT); includes four "
    "clickable filter buttons at the top (All, Matches, Confirmed Changes, "
    "Silent Drifts) that filter the visible cards by classification when "
    "clicked, with the active filter visually highlighted; and includes "
    "summary counts next to each filter button. Return ONLY the complete "
    "HTML code when this is requested, no other text."
)


def create_agent():
    """Run once to create the agent. Prints the ID to hardcode into AGENT_ID above."""
    agent = client.beta.agents.create(
        name="PRD vs Jira",
        description="Compares Confluence PRDs to linked Jira epics and flags silent drift",
        model="mistral-medium-latest",
        instructions=AGENT_INSTRUCTIONS,
        tools=[
            {
                "type": "connector",
                "connector_id": ATLASSIAN_CONNECTOR_ID,
            },
        ],
    )
    print(f"Agent created: {agent.id}")
    print("Copy this ID into AGENT_ID at the top of this file, then comment out create_agent() below.")
    return agent.id


def run_drift_check(prd_title: str):
    """Ask the agent for a JSON comparison of a named PRD vs its linked Jira epic."""
    prompt = f'Compare the Confluence page titled "{prd_title}" to its linked Jira epic.'

    response = client.beta.conversations.start(
        agent_id=AGENT_ID,
        inputs=[{"role": "user", "content": prompt}],
    )

    raw_text = ""
    for output in response.outputs:
        if output.type == "message.output":
            raw_text += output.content

    return raw_text


def generate_dashboard(prd_title: str, filename: str = "dashboard.html"):
    """Ask the agent to generate the full HTML dashboard for a named PRD comparison."""
    prompt = (
        f'Compare the Confluence page titled "{prd_title}" to its linked Jira epic, '
        f'then produce the HTML dashboard for this comparison.'
    )

    response = client.beta.conversations.start(
        agent_id=AGENT_ID,
        inputs=[{"role": "user", "content": prompt}],
    )

    html_text = ""
    for output in response.outputs:
        if output.type == "message.output":
            html_text += output.content

    with open(filename, "w") as f:
        f.write(html_text)
    print(f"Saved dashboard to {filename}")
    return html_text


def save_report(raw_json_text: str, filename: str = "drift_report.json"):
    """Parse and save the agent's JSON output to a file."""
    try:
        data = json.loads(raw_json_text)
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Saved report to {filename}")
        return data
    except json.JSONDecodeError:
        print("Warning: response wasn't clean JSON. Raw output:")
        print(raw_json_text)
        return None


if __name__ == "__main__":
    # Step 1: create the agent once, then comment this out and hardcode AGENT_ID above
    if AGENT_ID is None:
        AGENT_ID = create_agent()

    # Step 2: get the JSON comparison
    result_text = run_drift_check("Notification Settings Page")
    print(result_text)
    save_report(result_text)

    # Step 3: get the HTML dashboard directly from the agent
    generate_dashboard("Notification Settings Page")
