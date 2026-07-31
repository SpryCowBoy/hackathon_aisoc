"""
PRD vs Jira Drift Detector
Compares a Confluence PRD to its linked Jira epic using Mistral's
Atlassian connector, and classifies each requirement as
MATCHES, CONFIRMED_CHANGE, or SILENT_DRIFT.
"""

import os
import json
from mistralai.client import Mistral

# --- Setup ---
client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

ATLASSIAN_CONNECTOR_ID = "0198e70f-57b0-77f6-a752-0a7f5ea2da35"  # your connector ID
AGENT_ID = "ag_019fb9b41fec73afbb6ad6f758b727e1"  # your existing agent (already has connector attached)


def create_agent():
    """Run once to create the agent. Not needed again if AGENT_ID above is already set."""
    agent = client.beta.agents.create(
        name="PRD vs Jira",
        description="Compares Confluence PRDs to linked Jira epics and flags silent drift",
        model="mistral-medium-latest",
        instructions=(
            "You compare Confluence PRDs to their linked Jira epics and flag where "
            "scope has silently diverged without a corresponding change record. "
            "Explain why each mismatch likely happened."
        ),
        tools=[
            {
                "type": "connector",
                "connector_id": ATLASSIAN_CONNECTOR_ID,
            },
        ],
    )
    print(f"Agent created: {agent.id}")
    return agent.id


def run_drift_check(prd_title: str):
    """Ask the agent to compare a named PRD to its linked Jira epic, returning structured JSON."""
    prompt = f"""Compare the Confluence page titled "{prd_title}" to its linked Jira epic.
For each requirement, respond ONLY with a JSON array in this exact format, no other text:

[
  {{
    "requirement": "...",
    "jira_story": "...",
    "classification": "MATCHES" | "CONFIRMED_CHANGE" | "SILENT_DRIFT",
    "reason": "...",
    "likely_cause": "..."
  }}
]"""

    response = client.beta.conversations.start(
        agent_id=AGENT_ID,
        inputs=[{"role": "user", "content": prompt}],
    )

    raw_text = ""
    for output in response.outputs:
        if output.type == "message.output":
            raw_text += output.content

    return raw_text


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
    # Uncomment the line below only if you need to create the agent again:
    # AGENT_ID = create_agent()

    result_text = run_drift_check("Notification Settings Page")
    print(result_text)
    save_report(result_text)
