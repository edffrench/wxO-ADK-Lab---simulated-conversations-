#!/usr/bin/env python3
"""
Run `orchestrate evaluations generate` with a different LLM.

The ADK hard-codes `watsonx/openai/gpt-oss-120b` for synthetic test generation,
which is not enabled in every tenant (gateway returns HTTP 500). This wrapper
overrides the model_id passed to `get_provider` and then invokes the normal CLI.

Usage:
    python3 user_stories/generate_with_model.py [MODEL_ID] -- <generate args>
Example:
    python3 user_stories/generate_with_model.py groq/openai/gpt-oss-120b -- \
        -s user_stories/stories.csv -t user_stories/tools \
        -o user_stories/generated_tests -e .env
"""
import sys

import agentops.automatic_eval_generation.data_generator as dg
import agentops.service_provider as sp
from ibm_watsonx_orchestrate.cli.main import app

DEFAULT_MODEL = "groq/openai/gpt-oss-120b"


def main() -> None:
    argv = sys.argv[1:]
    model = DEFAULT_MODEL
    if argv and argv[0] != "--":
        model = argv.pop(0)
    if argv and argv[0] == "--":
        argv.pop(0)

    original = sp.get_provider

    def patched(*args, **kwargs):
        kwargs["model_id"] = model
        return original(*args, **kwargs)

    sp.get_provider = patched
    # Also patch any module that already imported the name directly.
    for mod in list(sys.modules.values()):
        if getattr(mod, "get_provider", None) is original:
            mod.get_provider = patched

    # Bypass Langfuse: the SaaS tenant has no Langfuse server, so replace the
    # Langfuse-backed tool-success filter with a pass-through stub.
    class _NoLangfuseFilter:
        def __init__(self, *args, **kwargs):
            pass

        def __getattr__(self, name):
            return lambda *a, **k: (a[0] if a else None)

    dg.LangfuseToolSuccessFilter = _NoLangfuseFilter

    print(f"[generate_with_model] forcing model_id={model}")
    sys.argv = ["orchestrate", "evaluations", "generate", *argv]
    app()


if __name__ == "__main__":
    main()
