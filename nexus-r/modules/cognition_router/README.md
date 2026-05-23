Cognition Router module contract:
1. Consume parsed intents.
2. Route only across local and BYOK tiers in Phase 1.
3. Prefer local for simple tasks.
4. Escalate to BYOK only if configured and complexity warrants it.
5. Check prior successful task traces before routing.
6. Emit deterministic routing decisions.
7. Expose estimated cost.
8. Record rationale for audit.
9. Never jump to unconfigured providers.
10. Deny unsupported premium tiers in Phase 1.
