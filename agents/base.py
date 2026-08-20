"""
MANDATE — Base Agent

Each agent is a genuinely independent entity with:
- Its own cryptographic identity (Ed25519 keypair)
- Its own declared scope (what it's authorized to do)
- Its own tool execution capability
- Its own process (when spawned by the coordinator)

The base agent provides the framework. Subclasses implement
the specific analysis logic for linting, security, and performance.
"""

import json
import sys
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Add project root to path for subprocess execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from governance.identity import AgentIdentity, create_agent_identity
from governance.audit import AuditTrail
from governance.authority import GovernanceManager
from armoriq_sdk.exceptions import PolicyBlockedException


@dataclass
class AgentResult:
    """Result from an agent's analysis run."""
    agent_id: str
    agent_role: str
    fingerprint: str
    public_key: str
    scopes: List[str]
    findings: List[Dict[str, Any]]
    actions_taken: List[Dict[str, Any]]
    status: str = "completed"
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_role": self.agent_role,
            "fingerprint": self.fingerprint,
            "public_key": self.public_key,
            "scopes": self.scopes,
            "findings": self.findings,
            "actions_taken": self.actions_taken,
            "status": self.status,
            "error": self.error,
        }


class BaseAgent:
    """Base class for all MANDATE agents."""

    def __init__(
        self,
        agent_id: str,
        agent_role: str,
        scopes: List[str],
        governed: bool = False,
        token_data: Optional[dict] = None,
    ):
        self.identity = create_agent_identity(agent_id, agent_role, scopes)
        self.governed = governed
        self.findings: List[Dict[str, Any]] = []
        self.actions_taken: List[Dict[str, Any]] = []
        self.audit = AuditTrail()
        
        self.governance = None
        if self.governed:
            self.governance = GovernanceManager(self.identity)
            if token_data:
                self.governance.load_token(token_data)

    def log(self, message: str):
        """Log with agent identity prefix. Uses stderr to keep stdout clean for JSON."""
        print(
            f"  [{self.identity.agent_role.upper()}:{self.identity.fingerprint[:8]}] {message}",
            file=sys.stderr,
        )

    def add_finding(self, finding: dict):
        """Record a finding from analysis."""
        self.findings.append(finding)
        self.audit.record_finding(
            agent_id=self.identity.agent_id,
            agent_role=self.identity.agent_role,
            tool=finding.get("tool", "unknown"),
            details=finding,
        )

    def check_authority(self, required_scope: str) -> bool:
        """Check if this agent has authority for an action.

        In ungoverned mode: always returns True (the point of the Day 1 demo).
        In governed mode: checks against ArmorIQ enforcement.
        """
        if not self.governed:
            self.audit.record_tool_request(
                agent_id=self.identity.agent_id,
                agent_role=self.identity.agent_role,
                tool=required_scope,
                action=required_scope,
                scopes=self.identity.scopes,
                decision="ALLOW",
                reason="UNGOVERNED — no authority check enforced",
            )
            return True
        else:
            try:
                # With governance — check against the intent token policy
                if self.governance:
                    self.governance.enforce_action(required_scope)
                is_authorized = True
                decision = "ALLOW"
                reason = f"Action '{required_scope}' is authorized by intent token"
            except PolicyBlockedException as e:
                is_authorized = False
                decision = "BLOCK"
                reason = str(e)
            except Exception as e:
                is_authorized = False
                decision = "BLOCK"
                reason = f"Enforcement error: {e}"
                
            self.audit.record_tool_request(
                agent_id=self.identity.agent_id,
                agent_role=self.identity.agent_role,
                tool=required_scope,
                action=required_scope,
                scopes=self.identity.scopes,
                decision=decision,
                reason=reason,
            )
            
            # Record it in actions_taken for the coordinator to display
            self.actions_taken.append({
                "action": required_scope,
                "status": "EXECUTED" if is_authorized else "BLOCKED",
                "reason": reason
            })
            
            return is_authorized

    def run(self, repo_path: str, changed_files: List[str]) -> AgentResult:
        """Execute the agent's analysis. Subclasses must implement this."""
        raise NotImplementedError("Subclasses must implement run()")

    def get_result(self) -> AgentResult:
        """Get the agent's result."""
        return AgentResult(
            agent_id=self.identity.agent_id,
            agent_role=self.identity.agent_role,
            fingerprint=self.identity.fingerprint,
            public_key=self.identity.public_key_hex,
            scopes=self.identity.scopes,
            findings=self.findings,
            actions_taken=self.actions_taken,
        )
