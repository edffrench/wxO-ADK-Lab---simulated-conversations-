# Evaluation Framework with wxO ADK
## Generating and Running Synthetic Conversations

**Skill level:** Beginner — no prior knowledge of watsonx Orchestrate or IBM Bob required  
**Estimated time:** 90 minutes  
**ADK version tested:** ibm-watsonx-orchestrate 2.19.x

---

## 💡 Recommended Approach: Use IBM Bob

This lab can be completed entirely from the command line using the steps below. However, if you have access to **IBM Bob**, we strongly recommend using it — Bob has an MCP server that connects directly to your watsonx Orchestrate instance, and skills that know how to build and test agents. With Bob you can deploy this agent, generate test cases, and run evaluations just by describing what you want in plain English.

To get set up with Bob:
1. Install Bob (ask your IBM contact or visit [ibm.com/bob](https://www.ibm.com/bob))
2. Install the **watsonx Orchestrate ADK MCP** from the Bob skill store
3. Fetch the `wxo-builder` skill: in Bob, type *"fetch skill wxo-builder"*

**If you don't have Bob, don't worry** — every step below gives you the exact command to run yourself.

---

## 🔍 What We're Building

You will deploy a **Mortgage Vulnerability & Regulatory Guidance Research Agent** — an AI assistant that helps mortgage case workers understand their regulatory obligations (FCA MCOB 13, Consumer Duty, FG21/1) when a customer asks for a payment holiday.

The agent uses the **Gemini API** to answer questions. In this lab, Gemini acts as a knowledgeable assistant drawing on its training data — a practical stand-in for a live Google Search. If you have access to the Gemini API's paid tier, you can enable the `google_search` grounding tool in `tools/gemini_web_search.py` with one line change and get live web results instead.

You will then:
- Write three synthetic user stories about a redundancy scenario
- Use the ADK to generate simulated conversations from those stories
- Run automated evaluations that score the agent on tool usage and answer quality
- Inspect the results

---

## 📁 Files Provided

You should have received these files. Check they are all present before starting.

| File | What it is |
|---|---|
| `mortgage_vulnerability_guidance_agent.yaml` | The agent definition — instructions, model, tools, guidelines |
| `tools/gemini_web_search.py` | The custom Gemini search tool the agent calls |
| `.env.example` | Template for your credentials — you will copy and fill this in |
| `user_stories/stories.csv` | Three pre-written story rows for the test generator |
| `user_stories/tools/gemini_search_tools.py` | Tool stubs that tell the generator what tools the agent has |
| `user_stories/generate_with_model.py` | Wrapper script that fixes a model-compatibility issue in the ADK generator |
| `user_stories/add_ground_truth.py` | Script that adds expected keywords and a reference answer to generated test cases |
| `user_stories/eval_config.yaml` | Configuration for the evaluation run |

---

## Part 0 — Prerequisites & Account Setup

### 0.1 Python

You need Python 3.11 or higher. Check with:

```bash
python3 --version
```

If you see `3.11.x` or higher, you're good. Otherwise install Python from [python.org/downloads](https://www.python.org/downloads).

---

### 0.2 Get a watsonx Orchestrate Instance

IBM offers a free 30-day trial of watsonx Orchestrate hosted on AWS.

1. Go to [ibm.com/products/watsonx-orchestrate](https://www.ibm.com/products/watsonx-orchestrate) and click **Start free trial**
2. Sign in with your IBM ID (or create one — it's free)
3. Choose the **AWS** deployment option and select the `eu-west-2` (London) or `us-east-1` (Virginia) region
4. Once provisioned, open your instance dashboard
5. Click your profile icon → **API keys** → **Generate API key**
6. Copy and save the key — you will only see it once. This is your `WO_API_KEY`.
7. Copy the **Service Instance URL** from the instance dashboard. It looks like:
   ```
   https://api.eu-west-2.dl.watson-orchestrate.ibm.com/instances/<your-instance-id>
   ```
   This is your `WO_SERVICE_INSTANCE_URL`.

---

### 0.3 Get a Gemini API Key

The Gemini API has a free tier that is sufficient for this lab.

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with a Google account
3. Click **Create API key** → **Create API key in new project**
4. Copy the key. This is your `GEMINI_API_KEY`.

> **Note on Google Search grounding:** the free Gemini API tier does not include live Google Search. In this lab the agent uses Gemini's own training knowledge to answer regulatory questions — this is accurate and useful for known regulations like MCOB 13. If you upgrade to the Gemini API paid tier, you can enable live search by adding `"tools": [{"google_search": {}}]` back to `tools/gemini_web_search.py`.

---

### 0.4 Install the ADK

```bash
pip install "ibm-watsonx-orchestrate[agentops]"
pip install "ibm-watsonx-orchestrate-evaluation-framework[langfuse]"
```

Verify:

```bash
orchestrate --version
```

You should see `ADK Version: 2.19.x` or higher.

---

### 0.5 Set Up Your Credentials File

Copy the template and fill in your three values:

```bash
cp .env.example .env
```

Open `.env` in a text editor and set:

```
WO_API_KEY=<your watsonx Orchestrate API key>
WO_SERVICE_INSTANCE_URL=https://api.<region>.dl.watson-orchestrate.ibm.com/instances/<id>
GEMINI_API_KEY=<your Gemini API key>
```

> Never commit `.env` to git. The `.env.example` file is safe to share; `.env` is not.

---

### 0.6 Connect the ADK to Your Instance

```bash
set -a; . ./.env; set +a

orchestrate env add \
  -n my-wxo \
  -u "$WO_SERVICE_INSTANCE_URL"

orchestrate env activate my-wxo --api-key "$WO_API_KEY"
```

Confirm it worked:

```bash
orchestrate agents list
```

You should see a table (possibly empty if this is a fresh instance). No error = connected.

> **Token expiry:** the token lasts a few hours. If you see `token missing or expired`, re-run the `env activate` command.

---

## Part 1 — Deploy the Mortgage Research Agent

### 1.1 Create the Gemini Connection

The agent's search tool reads its API key from a watsonx Orchestrate **connection** — a secure credential store. You need to create it and load your Gemini key.

```bash
# Create the connection (only needed once per instance)
orchestrate connections import -f connections/gemini_web_search_connection.yaml
```

> If you don't have a `connections/` folder in your lab files, you can create the connection manually:
> ```bash
> orchestrate connections create -a gemini_web_search_ibm_184bdbd3
> orchestrate connections configure \
>   -a gemini_web_search_ibm_184bdbd3 \
>   --kind key_value \
>   --type team \
>   --env draft
> ```

Now push your Gemini API key into it for both environments:

```bash
orchestrate connections set-credentials \
  -a gemini_web_search_ibm_184bdbd3 \
  --environment draft \
  --entries "api_key=$GEMINI_API_KEY"

orchestrate connections set-credentials \
  -a gemini_web_search_ibm_184bdbd3 \
  --environment live \
  --entries "api_key=$GEMINI_API_KEY"
```

Verify the key is set:

```bash
orchestrate connections list
```

You should see `gemini_web_search_ibm_184bdbd3` with a ✅ under **Credentials entered**.

---

### 1.2 Import the Gemini Search Tool

```bash
orchestrate tools import \
  -k python \
  -f tools/gemini_web_search.py \
  -a gemini_web_search_ibm_184bdbd3
```

Expected output:
```
[INFO] - Tool 'gemini_web_search' imported successfully
```

---

### 1.3 Import the Agent

```bash
orchestrate agents import -f mortgage_vulnerability_guidance_agent.yaml
```

Expected output:
```
[INFO] - Agent 'mortgage_vulnerability_guidance_agent' created successfully
```

If you see `updated` instead of `created`, the agent was already there — that's fine.

---

### 1.4 Verify the Deployment

```bash
orchestrate agents list
```

You should see `mortgage_vulnerability_guidance_agent` in the table. 

**Quick sanity test** — send a single message:

```bash
orchestrate chat ask \
  --agent-name mortgage_vulnerability_guidance_agent \
  "A customer has just been made redundant and wants a three-month payment holiday. What does MCOB 13 require?"
```

You should receive a structured answer covering MCOB 13 forbearance obligations. If you see a tool call in the output (the agent calling `gemini_web_search`), the tool integration is working end-to-end.

---

## Part 2 — Create Three Synthetic User Stories

### What is a user story in this context?

A **user story** is a one-sentence description of something a user wants to achieve. The ADK's test generator reads a CSV of stories and generates realistic opening messages and expected tool-call sequences from them.

### 2.1 Look at the Provided Stories

Open `user_stories/stories.csv`. It contains three rows, all based on the same redundancy scenario but each focused on a different question a case worker might ask:

```
story,agent
"Redundancy: ... The case worker asks the agent what MCOB 13 requires and which forbearance options to offer.",mortgage_vulnerability_guidance_agent
"Redundancy: ... The case worker is worried the customer is anxious and vulnerable and asks which FG21/1 adjustments and debt advice signposting apply.",mortgage_vulnerability_guidance_agent
"Redundancy: ... The case worker asks whether the firm must wait for arrears, and what the payment holiday means for accrued interest and the customer's credit file.",mortgage_vulnerability_guidance_agent
```

### 2.2 (Optional) Write Your Own Stories

You can add rows to the CSV to generate additional test cases. Each story should:
- Describe the customer situation
- Name the regulation in play
- State what the case worker wants to know

The `agent` column must exactly match the agent's `name` field in the YAML (`mortgage_vulnerability_guidance_agent`).

---

## Part 3 — Generate Ground Truth Test Cases

### What is "ground truth"?

Ground truth tells the evaluator what a *correct* agent response looks like. Without it, the evaluator can only check whether the agent responded — not whether the response was any good.

In this lab, ground truth has two parts:
1. **Expected tool calls** — which tools should the agent call, and in what order
2. **Expected keywords** — words or phrases that should appear in the answer (e.g. "MCOB", "forbearance", "MoneyHelper")

### 3.1 Generate Test Cases from Stories

The ADK's `orchestrate evaluations generate` command creates test case JSON files from your CSV. It uses an LLM to infer what tool calls a good agent would make.

Run this wrapper script (it fixes a model-compatibility issue — see the Troubleshooting section):

```bash
set -a; . ./.env; set +a

python3 user_stories/generate_with_model.py groq/openai/gpt-oss-120b -- \
  -s user_stories/stories.csv \
  -t user_stories/tools/gemini_search_tools.py \
  -o user_stories/generated_tests \
  -e .env
```

Expected output:
```
[INFO] Generated 3 evaluation cases for agent 'mortgage_vulnerability_guidance_agent'
[INFO] Test cases stored at: user_stories/generated_tests
```

Three JSON files will appear in `user_stories/generated_tests/mortgage_vulnerability_guidance_agent_test_cases/`.

> **Why the wrapper?** The `generate` command hard-codes the model `watsonx/openai/gpt-oss-120b` for test generation. This model is not enabled on all tenants. The wrapper overrides it with `groq/openai/gpt-oss-120b`, which is available. It also patches out a Langfuse dependency that requires a local Docker server we don't have running.

> **Why `gemini_search_tools.py`?** Without a tool definition file, the generator invents fake tool names. The stub file tells it that the agent has a `gemini_web_search` tool, so the generated test cases expect that tool to be called.

---

### 3.2 Add Keywords and Reference Answers

The generated files contain expected tool calls but no expected *answer content*. Run the ground-truth script to add keywords and a reference summary:

```bash
python3 user_stories/add_ground_truth.py
```

This creates enriched copies in `user_stories/test_cases/`. The originals in `generated_tests/` are untouched.

**What it adds to each test case:**

| Addition | Detail |
|---|---|
| `summarize` goal | A text goal that checks the agent's final answer |
| `keywords` | Terms the answer must contain: MCOB, forbearance, FG21/1, interest, credit, MoneyHelper, StepChange, and 2 per-case extras |
| `response` | A reference summary describing what a correct answer looks like |
| `arg_matching: ignore` | Stops the evaluator failing a correct agent just because its search query wording differs from the generated one |

---

### 3.3 Inspect a Test Case

Open any of the three JSON files in `user_stories/test_cases/`. You will see:

```json
{
  "agent": "mortgage_vulnerability_guidance_agent",
  "starting_sentence": "Can you explain what MCOB 13 requires and which forbearance options I should offer?",
  "story": "Redundancy: ...",
  "goals": {
    "gemini_web_search_1": ["summarize"],
    "gemini_web_search_2": ["summarize"],
    "summarize": []
  },
  "goal_details": [
    { "type": "tool_call", "name": "gemini_web_search_1", "tool_name": "gemini_web_search", "args": { "query": "..." }, "arg_matching": { "query": "ignore" } },
    { "type": "tool_call", "name": "gemini_web_search_2", "tool_name": "gemini_web_search", "args": { "query": "..." }, "arg_matching": { "query": "ignore" } },
    { "type": "text", "name": "summarize", "keywords": ["MCOB", "forbearance", ...], "response": "..." }
  ]
}
```

The `goals` map is a dependency graph. `gemini_web_search_1` and `gemini_web_search_2` both feed into `summarize`, meaning the evaluator expects the agent to search twice and then produce a summary that matches the keywords.

---

## Part 4 — Run Automated Evaluations

### What happens during an evaluation?

The ADK spins up a **simulated user** (powered by an LLM) and a **judge** (another LLM). The simulated user sends the `starting_sentence` to your deployed agent and continues the conversation for up to `max_user_turns` turns. The judge then scores the conversation against the ground truth.

### 4.1 Check the Evaluation Config

Open `user_stories/eval_config.yaml`:

```yaml
test_paths:
  - user_stories/test_cases/af1d7649-1dd0-43f3-b2b1-6840b285645f.json
output_dir: user_stories/results
max_user_turns: 2
llm_user_config:
  model_id: groq/openai/gpt-oss-120b
  provider_config:
    model_id: groq/openai/gpt-oss-120b
evaluation_config:
  provider_config:
    model_id: groq/openai/gpt-oss-120b
```

> **Why `groq/openai/gpt-oss-120b` for the judge?** The default judge model (`watsonx/openai/gpt-oss-120b`) is not enabled on all tenants and returns an HTTP 500. This config overrides it with a model that is available.

> **To run all three cases** change `test_paths` to `- user_stories/test_cases` (the whole directory). For a quick single-case run, point at one file as shown above.

---

### 4.2 Run the Evaluation

```bash
set -a; . ./.env; set +a

orchestrate evaluations evaluate \
  -c user_stories/eval_config.yaml \
  -e .env
```

This takes 1–4 minutes depending on how many cases you run. You will see progress in the terminal:

```
[INFO] Starting evaluation run for 1 test cases
[INFO] Processed 1/1 test cases
[INFO] Completed all 1 evaluations
```

Results are written to `user_stories/results/<timestamp>/`.

---

## Part 5 — Inspect Results

### 5.1 Results Folder Structure

```
user_stories/results/2026-10-26_18-38-32/
├── summary_metrics.csv       ← one row per test case, all scores
├── average_metrics.json      ← averaged scores across all cases
├── config.yml                ← copy of the eval config used
└── messages/
    └── <case-id>.messages.json   ← full conversation transcript
```

---

### 5.2 Reading `summary_metrics.csv`

Open in Excel or a text editor. Key columns:

| Column | What it measures |
|---|---|
| `is_success` | Did the case pass overall? (`True` / `False`) |
| `total_tool_calls` | How many tools did the agent call? |
| `expected_tool_calls` | How many were expected? |
| `correct_tool_calls` | How many matched the ground truth tool name? |
| `keyword_match` | Did the answer contain all expected keywords? (`True` / `False`) |
| `semantic_match` | Did the answer semantically match the reference summary? (`True` / `False`) |
| `average_agent_response_time` | How long did the agent take to respond (seconds)? |
| `orchestrate_agent_routing_accuracy` | Did the right agent handle the conversation? (1.0 = correct) |
| `text_match_comment` | Human-readable summary of the text goal result |

---

### 5.3 Reading the Conversation Transcript

Open `messages/<case-id>.messages.json`. Each entry is a turn:

```json
{ "role": "user",      "type": "text",          "content": "Can you explain what MCOB 13 requires..." }
{ "role": "assistant", "type": "tool_call",      "content": { "name": "gemini_web_search", "args": { "query": "..." } } }
{ "role": "assistant", "type": "tool_response",  "content": "Under MCOB 13 the lender is bound by..." }
{ "role": "assistant", "type": "text",           "content": "**Executive Summary** ..." }
```

Look for:
- Did the agent call `gemini_web_search` on the first message? (The lab instructions require this)
- Did the tool return a real answer, or an error?
- Was the final answer concise (the instructions ask for under 250 words)?
- Did the simulated user loop on pleasantries, or stop cleanly?

---

### 5.4 What the Scores Mean in Practice

| Score | Likely meaning |
|---|---|
| `is_success: False`, tool calls = 0 | Agent answered from training knowledge without searching — check mandatory-search instructions |
| `is_success: False`, keyword miss | Answer covered the topic but used different terminology — check ground truth keywords |
| `is_success: False`, tool name mismatch | Ground truth has wrong tool name — update `add_ground_truth.py` and regenerate |
| `is_success: True` | Agent called the tool, produced a keyword-matching, semantically correct answer |
| `semantic_match: True` but `is_success: False` | Text goal passed but tool-call goals failed — agent knows the answer but didn't search |

---

## Troubleshooting

### "token missing or expired"
```bash
set -a; . ./.env; set +a
orchestrate env activate my-wxo --api-key "$WO_API_KEY"
```

### "No module named 'agentops'"
```bash
pip install --upgrade "ibm-watsonx-orchestrate[agentops]"
```

### "Langfuse is not installed"
```bash
pip install "ibm-watsonx-orchestrate-evaluation-framework[langfuse]"
```
The `Authentication error: Langfuse client initialized without public_key` warning that follows is harmless — the Langfuse client is disabled and the generator continues without it.

### "500 Server Error" from the gateway during `generate`
The generator is trying to use a model not enabled on your tenant. Make sure you are using `generate_with_model.py` (Step 3.1), not calling `orchestrate evaluations generate` directly.

### "500 Server Error" from the gateway during `evaluate`
Make sure `eval_config.yaml` has `llm_user_config.model_id: groq/openai/gpt-oss-120b` and `evaluation_config.provider_config.model_id: groq/openai/gpt-oss-120b`. Without this config the evaluator uses `watsonx/openai/gpt-oss-120b` which may not be available.

### "No tools found with the name 'gemini_web_search'"
The tool wasn't imported, or was imported under a different name. Run:
```bash
orchestrate tools list
```
If `gemini_web_search` is missing, re-run Step 1.2.

### "Gemini API error (HTTP 404): This model is no longer available"
The Gemini model name in `tools/gemini_web_search.py` is outdated. Open the file, find `DEFAULT_MODEL`, and update it to a current model name. Re-import the tool:
```bash
orchestrate tools import -k python -f tools/gemini_web_search.py -a gemini_web_search_ibm_184bdbd3
```

### "API key not valid" in the tool response
Your Gemini key in the connection is expired or incorrect. Re-set it:
```bash
orchestrate connections set-credentials \
  -a gemini_web_search_ibm_184bdbd3 \
  --environment draft \
  --entries "api_key=<your-new-key>"
```
Note: the flag is `--environment`, not `--env`.

### Generator produces test cases with invented tool names
You ran the generator without a tools file. Clear the output folder and re-run with `-t user_stories/tools/gemini_search_tools.py` as shown in Step 3.1.

---

## Going Further

### Enable live Google Search grounding
In `tools/gemini_web_search.py`, change the request body from:
```python
body = json.dumps({
    "contents": [{"parts": [{"text": query[:500]}]}],
}).encode("utf-8")
```
to:
```python
body = json.dumps({
    "contents": [{"parts": [{"text": query}]}],
    "tools": [{"google_search": {}}],
}).encode("utf-8")
```
This requires a Gemini API key with the Search Grounding feature enabled (paid tier). Also add source-link parsing back to the response parser — see `WXO_AGENT_ADK_GUIDE.md` section 8.14 for the original implementation.

### Add your own test stories
Add rows to `user_stories/stories.csv`, clear `user_stories/generated_tests/`, and re-run Steps 3.1 and 3.2.

### Run all three cases
In `user_stories/eval_config.yaml`, change:
```yaml
test_paths:
  - user_stories/test_cases
```
and set `max_user_turns: 3`.

### Red-team the agent
```bash
orchestrate evaluations red-teaming --help
```
This generates adversarial prompts designed to make the agent bypass MCOB 13 rules or waive Consumer Duty protections.

### Use the local Developer Edition with Langfuse
If you have Docker installed and a watsonx Orchestrate entitlement key:
```bash
orchestrate server start -e .env -l --accept-terms-and-conditions
orchestrate env activate local
```
The `-l` flag starts a local Langfuse server. Once running, remove the Langfuse bypass from `generate_with_model.py` for full tool-success filtering in generated test cases.

---

## Quick Reference: All Lab Commands

```bash
# --- Setup ---
pip install "ibm-watsonx-orchestrate[agentops]"
pip install "ibm-watsonx-orchestrate-evaluation-framework[langfuse]"
cp .env.example .env                        # fill in your keys
set -a; . ./.env; set +a                    # load keys into shell
orchestrate env add -n my-wxo -u "$WO_SERVICE_INSTANCE_URL"
orchestrate env activate my-wxo --api-key "$WO_API_KEY"

# --- Part 1: Deploy ---
orchestrate connections set-credentials -a gemini_web_search_ibm_184bdbd3 --environment draft --entries "api_key=$GEMINI_API_KEY"
orchestrate connections set-credentials -a gemini_web_search_ibm_184bdbd3 --environment live  --entries "api_key=$GEMINI_API_KEY"
orchestrate tools import -k python -f tools/gemini_web_search.py -a gemini_web_search_ibm_184bdbd3
orchestrate agents import -f mortgage_vulnerability_guidance_agent.yaml
orchestrate agents list                     # confirm deployment

# --- Part 3: Generate test cases ---
python3 user_stories/generate_with_model.py groq/openai/gpt-oss-120b -- \
  -s user_stories/stories.csv \
  -t user_stories/tools/gemini_search_tools.py \
  -o user_stories/generated_tests \
  -e .env
python3 user_stories/add_ground_truth.py

# --- Part 4: Evaluate ---
orchestrate evaluations evaluate -c user_stories/eval_config.yaml -e .env

# --- Refresh an expired token ---
orchestrate env activate my-wxo --api-key "$WO_API_KEY"

# --- Update the tool after code changes ---
orchestrate tools import -k python -f tools/gemini_web_search.py -a gemini_web_search_ibm_184bdbd3

# --- Update the agent after YAML changes ---
orchestrate agents import -f mortgage_vulnerability_guidance_agent.yaml
```

---

*For the full build log, error history, and design decisions behind every file in this lab, see `WXO_AGENT_ADK_GUIDE.md`.*
