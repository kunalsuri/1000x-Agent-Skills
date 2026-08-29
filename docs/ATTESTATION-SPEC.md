# 🛡️ Attestation Specification — Proven Capability

In **1000x-Agent-Skills**, every production skill is **Attested**. Attestation is the formal verification that a skill has been tested in real agent environments against specific LLM backends.

---

## 📄 Schema: `attestation.json`

Every skill directory contains an `attestation.json` file structured as follows:

```json
{
  "$schema": "https://raw.githubusercontent.com/kunalsuri/1000x-Agent-Skills/main/docs/schemas/attestation.schema.json",
  "skill_name": "resumable-sdd",
  "version": "1.1.0",
  "attestation_status": "VERIFIED",
  "attested_by": "Kunal Suri",
  "attestation_date": "2026-08-29",
  "tested_platforms": [
    {
      "platform": "Claude Code",
      "model": "claude-3-7-sonnet",
      "status": "PASS",
      "notes": "Survives simulated 50k token context exhaustion and resumes from checklist."
    },
    {
      "platform": "Google Antigravity",
      "model": "gemini-3.7-flash",
      "status": "PASS",
      "notes": "Autonomous planning and checklist generation verified."
    }
  ],
  "performance_summary": {
    "success_rate_percent": 100,
    "average_token_consumption": 1450,
    "recovery_resilience": "High"
  },
  "provenance": {
    "source_type": "original",
    "origin_url": "https://github.com/kunalsuri/1000x-Agent-Skills",
    "license": "Apache-2.0"
  }
}
```

---

## 🎖️ Attestation Status Levels

| Status | Badge | Definition |
|---|---|---|
| **DRAFT** | `🟡 Draft` | Authored and passes linter, but pending multi-model evaluation. |
| **TESTED** | `🔵 Tested` | Evaluated on at least 1 primary model with passing trigger test suite. |
| **VERIFIED** | `🟢 Verified` | Multi-platform verified with proven resilience logs in production or classroom tasks. |
| **DEPRECATED** | `🔴 Deprecated` | Superseded by newer workflows or updated agent runtime APIs. |
