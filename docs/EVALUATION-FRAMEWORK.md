# 📊 Evaluation Framework — Trigger Precision & Output Quality

To ensure agent skills are reliable and non-intrusive, each skill includes an automated evaluation harness under `evals/`.

---

## 🎯 Evaluation Objectives

1. **Trigger Precision (True Positives)**: Does the agent automatically invoke the skill when the user provides an intent matched by the skill's description?
2. **Trigger Specificity (True Negatives)**: Does the skill stay inert when the user is asking unrelated questions (preventing token wastage)?
3. **Execution Success**: Does following the skill produce the intended artifact or code state?

---

## 🧪 Evaluation Test Schema (`evals/test-cases.json`)

```json
{
  "skill_name": "resumable-sdd",
  "version": "1.1.0",
  "trigger_evaluation": {
    "positive_prompts": [
      {
        "id": "pos-01",
        "prompt": "We need to build a complex multi-step auth system. Make sure we commit progress so we don't lose context if token limits hit.",
        "expected_trigger": true
      },
      {
        "id": "pos-02",
        "prompt": "Start a new feature using spec-driven development with a checklist.",
        "expected_trigger": true
      }
    ],
    "negative_prompts": [
      {
        "id": "neg-01",
        "prompt": "Fix this typo in line 42 of index.html",
        "expected_trigger": false
      },
      {
        "id": "neg-02",
        "prompt": "Explain what a binary search tree is.",
        "expected_trigger": false
      }
    ]
  }
}
```

---

## 📈 Scoring Metrics

- **Trigger Recall**: $\frac{\text{True Positives}}{\text{True Positives} + \text{False Negatives}} \ge 90\%$
- **Trigger Precision**: $\frac{\text{True Positives}}{\text{True Positives} + \text{False Positives}} \ge 85\%$
- **Health Score (Skill Doctor)**: $\ge 85 / 100$
