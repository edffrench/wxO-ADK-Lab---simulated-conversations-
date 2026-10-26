#!/usr/bin/env python3
"""
Copy generated test cases to user_stories/test_cases/ and add response ground truth:
  - a `summarize` goal (type text) with expected keywords and a reference summary
  - arg_matching=ignore on the search query (the agent's wording will differ)
Generated files are never modified, so re-running `generate` is safe.

Usage: python3 user_stories/add_ground_truth.py
"""
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "generated_tests"
DST = ROOT / "test_cases"

RUNTIME_TOOL_NAME = "gemini_pro_search"

# Shared by all cases (redundancy / MCOB 13 story).
KEYWORDS = [
    "MCOB",  # not "MCOB 13": the agent writes it with a narrow no-break space (U+202F)
    "forbearance",
    "vulnerab",
    "FG21/1",
    "interest",
    "credit",
    "MoneyHelper",
    "StepChange",
]

# Per-case extras, matched on the case-worker question in the story text.
EXTRA = [
    ("what MCOB 13 requires", ["interest-only", "term extension"]),
    ("FG21/1 adjustments", ["Consumer Duty", "debt advice"]),
    ("must wait for arrears", ["arrears", "accrued interest"]),
]

SUMMARY = (
    "The customer has been made redundant, has no savings and has asked for a three-month "
    "payment holiday before any payment is missed. MCOB 13 expects the firm to act proactively "
    "on forbearance and not wait for arrears. The customer shows FG21/1 vulnerability drivers "
    "(life event: job loss; resilience: no savings), so servicing adjustments and signposting "
    "to free debt advice (MoneyHelper, StepChange) apply. The agent should evaluate the payment "
    "holiday including accrued interest and credit file impact, offer alternatives such as an "
    "interest-only switch or term extension under the Mortgage Charter, remind the case worker "
    "to verify affordability, and cite its sources."
)


def main() -> None:
    DST.mkdir(exist_ok=True)
    for path in sorted(glob.glob(str(SRC / "*" / "*.json"))):
        case = json.load(open(path))
        story = case["story"]
        extra = next((k for q, k in EXTRA if q in story), [])

        for g in case["goal_details"]:
            if g["type"] == "tool_call":
                # The generator uses the import ID; at runtime the agent calls it `gemini_pro_search`.
                g["tool_name"] = RUNTIME_TOOL_NAME
                if g.get("args"):
                    g["arg_matching"] = {k: "ignore" for k in g["args"]}

        tool_goals = [g["name"] for g in case["goal_details"]]
        case["goals"] = {name: ["summarize"] for name in tool_goals}
        case["goals"]["summarize"] = []
        case["goal_details"].append(
            {
                "type": "text",
                "name": "summarize",
                "keywords": KEYWORDS + extra,
                "response": SUMMARY,
            }
        )

        out = DST / Path(path).name
        json.dump(case, open(out, "w"), indent=2)
        print("wrote", out.relative_to(ROOT.parent))


if __name__ == "__main__":
    main()
