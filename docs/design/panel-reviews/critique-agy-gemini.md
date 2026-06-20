# Adversarial Critique: Carrier-Comms Optimization Plan
**Reviewer:** critique-agy (powered by Gemini)
**Date:** 2026-06-20
**Session:** comms-panel
**Target Document:** `docs/design/carrier-comms.md` & `docs/design/carrier-comms-buildplan.md`

---

## Executive Summary
The two-lever optimization plan is mathematically logical but relies on assumptions about LLM tool-calling economics and cognitive behavior that are likely incorrect in practice. 
* **Lever 1 (Channel Compression)** is highly likely to cause a **net token cost increase** rather than a wash or saving, because stripping code from the initial context (pack bundle) forces the agent to make extra tool calls (e.g., `view_file`), which multiplies prompt tokens over multiple turns.
* **Lever 2 (Polymath Handoff)** ignores the **3x–5x price premium of output tokens** over input tokens. Self-emitting reasoning residue is a high-cost operation that may exceed the cost of the receiver re-deriving the solution.
* **The evaluation protocol (N=3)** is statistically under-powered to locate a U-curve knee or detect regressions under stochastic LLM behavior.

Below is the detailed breakdown of these vulnerabilities, followed by specific, actionable corrections.

---

## 1. The Multi-Turn Tool Tax (Lever 1's Flawed Assumption)
The plan assumes that "re-reading code is cheap (shared disk; any carrier can grep)." While this is true for the disk, it is false for the LLM context window due to **multi-turn prompt accumulation**.

When we pointer-ize code slices (Move 4) or compress the pack:
1. The carrier receives a pointer: `repo://src/pigeon/tokens.py:142-166`.
2. The carrier must make a tool call to read that file.
3. Every tool call adds a turn to the conversation.
4. Each new turn re-sends the **entire chat history** (system prompt, previous messages, tool outputs) to the API.

### The Math:
* **Scenario A (Inlined Code):** We send a 1,000-token code slice inline in the pack. It costs **1,000 input tokens** once. The task is completed in 1 turn.
  * *Total Cost:* 1,000 tokens.
* **Scenario B (Pointer-ized):** We send a 50-token pointer. The history is 8,000 tokens. The agent calls `view_file` to read the 1,000-token slice. This adds 1 turn.
  * *Turn 1 Prompt:* 8,000 tokens.
  * *Turn 2 Prompt:* 8,000 (history) + 1,000 (tool output) = 9,000 tokens.
  * *Total Cost:* 17,000 tokens.

By removing 950 tokens from the initial pack, we forced an extra turn that cost **16,000 extra input tokens**. The "cheap re-reading" assumption is a massive token multiplier in multi-turn environments.

---

## 2. The Asymmetry of Output Tokens (Lever 2's Economic Reality)
The plan's win bar is defined in raw tokens. However, in production, **USD cost is the only metric that matters**, and output tokens are priced 3x to 5x higher than input tokens.

Under Lever 2 (self-emission):
* The sender must generate and write the `state.derived` object (ruled-out paths, constraints, rationale).
* Let's say this residue is 300 tokens. At a 5x output multiplier, this costs the equivalent of **1,500 input tokens** for the sender.
* The receiver then reads it, costing **300 input tokens**.
* *Total Cost of Residue:* 1,800 input-equivalent tokens.

If a capable receiver could have re-derived the same constraint or path on its own using less than 1,800 input-equivalent tokens (which is highly likely for minor constraints), self-emission is a **net financial loss**, even if it saves a few input tokens on the receiver's end. 

---

## 3. Statistical Insufficiency of $N=3$
LLMs are stochastic engines. Their tool-use paths, reasoning depth, and constraint adherence vary from run to run due to temperature and non-deterministic API execution.
* With $N=3$, the confidence interval for success rates and token counts is extremely wide.
* A single run failing due to a fluke (e.g., a minor formatting parsing error or API hiccup) drops the success rate from 100% to 66%.
* Under the U-curve stop rule, a false positive (believing a compressed config is safe when it is actually degraded) or a false negative (killing a good config because of one bad run) is highly probable.
* To reliably locate the "knee" of a U-curve, we need a larger sample size ($N \ge 8$) or a sequential testing framework to screen out noise.

---

## 4. Attention Dilution and JSON Nesting
The Fork-A capability finding proved that carrying a constraint prevents regressions. However, Fork-A injected this constraint as part of the *direct prompt*.
* The plan proposes putting the residue in a structured `state.derived` JSON object inside the handoff file.
* Many models (especially free models like `mimo` or `qwen`) suffer from **attention dilution** when constraints are buried deep within structured JSON payloads rather than formatted as explicit markdown in the system prompt.
* There is a risk that the model will write the `derived` schema successfully but ignore the contents of `derived` during its actual execution step because it does not attend to nested JSON fields as strongly as direct prompt instructions.

---

## 5. Ops Vulnerability: Cascading Timeouts and OAuth Expirations
The Phase-0 panel synthesis highlights a critical ops bottleneck: free models timed out at 600s, and Google OAuth expired.
* In a multi-agent coordinate run, a timeout or authentication failure at hop $K$ of $N$ invalidates the entire sequence.
* The build plan contains no mechanism for **checkpointing, state serialization, or resumption**.
* If a 3-hop cross-model run fails at the final step, we must pay the token cost to re-run the entire pipeline from the beginning. This makes the harness fragile and expensive to run.

---

## Actionable Recommendations
1. **Model the Multi-Turn Tool Tax:** Update `bench_join` to track `number_of_turns` per task. If compressing the pack increases the number of turns, the config must be heavily penalized.
2. **Weight Tokens by USD Price:** The "net token win" rule in Phase 3 and Phase 5 must be converted to a **USD net cost win**, applying the specific input/output pricing ratios of the models used (e.g., 1:5 for Claude 3.5 Sonnet).
3. **Flat Markdown Injection:** Do not rely on the receiver parsing `state.derived` from raw JSON. The coordinate harness must extract `state.derived` and inject it as a highly visible, top-level markdown block (`### Constraints Discovered in Prior Runs`) at the very top of the receiver's prompt.
4. **Implement Run Checkpointing:** Modify the coordinator so that successful hops are cached, allowing the pipeline to resume from the last successful handoff in the event of a timeout or authentication failure.
5. **Expand Sample Size for Final Gates:** Keep $N=3$ for initial screening, but require $N \ge 8$ before declaring a final "GO" on Lever 1 or Lever 2.
