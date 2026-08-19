"""
MANDATE — Audit Trail

Records every authorization decision for traceability.
The judge must be able to follow:

    USER INTENT → COORDINATOR → DELEGATION → AGENT → ACTION → DECISION

This is not decorative logging — it is the evidence that governance works.
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AuditEvent:
    """A single auditable event in the MANDATE governance chain."""

    timestamp: str
    event_type: str  # tool_request, authorization_decision, delegation, finding
    agent_id: str
    agent_role: str
    parent_agent: Optional[str] = None
    delegation_id: Optional[str] = None
    scope: Optional[List[str]] = None
    tool: Optional[str] = None
    action: Optional[str] = None
    decision: Optional[str] = None  # ALLOW, BLOCK, HOLD
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # Remove None values for cleaner output
        return {k: v for k, v in d.items() if v is not None}


class AuditTrail:
    """Collects and persists MANDATE audit events.

    Every meaningful action — tool requests, authorization decisions,
    delegations, findings — is recorded with full context.
    """

    def __init__(self, output_dir: Optional[str] = None):
        self.events: List[AuditEvent] = []
        self.output_dir = output_dir

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def record_delegation(
        self,
        coordinator_id: str,
        agent_id: str,
        agent_role: str,
        scopes: List[str],
        delegation_id: Optional[str] = None,
    ) -> AuditEvent:
        """Record a delegation event — coordinator grants authority to sub-agent."""
        event = AuditEvent(
            timestamp=self._now(),
            event_type="delegation",
            agent_id=agent_id,
            agent_role=agent_role,
            parent_agent=coordinator_id,
            delegation_id=delegation_id,
            scope=scopes,
            decision="DELEGATED",
            reason=f"Coordinator delegated {', '.join(scopes)} to {agent_role}",
        )
        self.events.append(event)
        return event

    def record_tool_request(
        self,
        agent_id: str,
        agent_role: str,
        tool: str,
        action: str,
        scopes: List[str],
        decision: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Record a tool invocation and its authorization decision."""
        event = AuditEvent(
            timestamp=self._now(),
            event_type="authorization_decision",
            agent_id=agent_id,
            agent_role=agent_role,
            tool=tool,
            action=action,
            scope=scopes,
            decision=decision,
            reason=reason,
            details=details,
        )
        self.events.append(event)
        return event

    def record_finding(
        self,
        agent_id: str,
        agent_role: str,
        tool: str,
        details: Dict[str, Any],
    ) -> AuditEvent:
        """Record a finding from an agent's analysis."""
        event = AuditEvent(
            timestamp=self._now(),
            event_type="finding",
            agent_id=agent_id,
            agent_role=agent_role,
            tool=tool,
            details=details,
        )
        self.events.append(event)
        return event

    def get_events(self) -> List[dict]:
        """Get all events as dicts."""
        return [e.to_dict() for e in self.events]

    def get_delegation_chain(self) -> List[dict]:
        """Extract the delegation chain for display."""
        return [
            e.to_dict() for e in self.events
            if e.event_type == "delegation"
        ]

    def get_authorization_decisions(self) -> List[dict]:
        """Extract authorization decisions for display."""
        return [
            e.to_dict() for e in self.events
            if e.event_type == "authorization_decision"
        ]

    def get_blocked_actions(self) -> List[dict]:
        """Extract blocked actions — the critical demo evidence."""
        return [
            e.to_dict() for e in self.events
            if e.decision == "BLOCK"
        ]

    def display(self) -> str:
        """Format the audit trail for terminal display."""
        lines = [
            "",
            "=" * 60,
            "MANDATE — AUDIT TRAIL",
            "=" * 60,
        ]
        for event in self.events:
            d = event.to_dict()
            icon = {
                "delegation": "🔗",
                "authorization_decision": "🛡️" if d.get("decision") == "BLOCK" else "✅",
                "finding": "🔍",
            }.get(d["event_type"], "📋")

            decision_str = ""
            if d.get("decision"):
                decision_str = f" [{d['decision']}]"

            lines.append(f"  {icon} [{d['timestamp'][:19]}] {d['event_type']}{decision_str}")
            lines.append(f"     Agent: {d['agent_role']} ({d['agent_id']})")
            if d.get("tool"):
                lines.append(f"     Tool:  {d['tool']} → {d.get('action', 'N/A')}")
            if d.get("scope"):
                lines.append(f"     Scope: {', '.join(d['scope'])}")
            if d.get("reason"):
                lines.append(f"     Reason: {d['reason']}")
            lines.append("")

        lines.append("=" * 60)
        blocked = self.get_blocked_actions()
        lines.append(f"  Total events: {len(self.events)}")
        lines.append(f"  Blocked actions: {len(blocked)}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def save(self, filepath: str) -> None:
        """Save audit trail to JSON file."""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.get_events(), f, indent=2)
