"""
Closira AI Customer Support Workflow
Powered by Anthropic Claude

Stages:
  1. FAQ Answering       - Answer from SOP only
  2. Lead Qualification  - Collect structured customer info
  3. Escalation Detection - Detect and log handoff triggers
  4. Conversation Summary - Generate structured end-of-session summary
"""

import json
import os
import datetime
import anthropic

# ── Config ────────────────────────────────────────────────────────────────────

SOP_PATH = "sop.json"
LOG_DIR  = "logs"
MODEL    = "claude-sonnet-4-20250514"

QUALIFICATION_QUESTIONS = [
    "What type of treatment are you interested in — Botox, Fillers, or would you like a free consultation first?",
    "Have you had any aesthetic treatments before, or would this be your first time?",
    "Is there a particular date or time that works best for you to come in?",
]

ESCALATION_KEYWORDS = [
    "complaint", "unhappy", "disgusted", "furious", "terrible", "awful",
    "speak to a human", "speak to someone", "talk to a person", "manager",
    "supervisor", "refund", "sue", "legal", "allergy", "medication",
    "contraindication", "pregnant", "breastfeeding", "discount", "cheaper",
    "negotiate", "better price",
]

# ── Load SOP ──────────────────────────────────────────────────────────────────

def load_sop(path: str) -> str:
    with open(path, "r") as f:
        data = json.load(f)
    return json.dumps(data, indent=2)

# ── Build System Prompt ───────────────────────────────────────────────────────

def build_system_prompt(sop_text: str) -> str:
    return f"""You are Bloom, a friendly and professional AI customer support assistant for Bloom Aesthetics Clinic.

## YOUR ROLE
You handle inbound customer enquiries across four stages:
1. Answer questions using ONLY the SOP data below
2. Qualify leads by asking structured questions
3. Detect when to escalate to a human agent
4. Produce a structured conversation summary at session end

## SOP DATA (Your only source of truth)
```json
{sop_text}
```

## STRICT RULES

### Hallucination Prevention
- ONLY answer questions using facts explicitly present in the SOP above.
- If a question is not covered by the SOP, say: "I don't have that information available right now."
- NEVER invent prices, procedures, availability, or medical advice.
- If unsure, always acknowledge the gap and offer to escalate.

### Escalation Detection
You MUST escalate immediately if ANY of the following occur:
- The customer expresses anger, frustration, or a complaint
- The customer asks a medical question (contraindications, medications, allergies, pregnancy)
- The customer requests a discount or price negotiation
- More than 2 questions cannot be answered from the SOP
- The customer asks to speak to a human, manager, or supervisor

When escalating, respond with this EXACT JSON block (fenced in ```json):
```json
{{"action": "ESCALATE", "reason": "<brief reason>", "sentiment": "<calm|frustrated|angry>"}}
```
Then add a warm human-readable message explaining the handoff.

### Qualification Phase
After answering initial questions, naturally transition into asking qualification questions:
1. Treatment interest (Botox / Fillers / Consultation)
2. Previous treatment experience
3. Preferred appointment timing

Ask ONE question at a time. Store answers mentally to include in the summary.

### Tone & Persona
- Warm, professional, and reassuring — like a knowledgeable receptionist
- Use first-person ("I'd be happy to help...")
- Keep responses concise (2–4 sentences for FAQ answers)
- Never use jargon or clinical language unless the customer does first
- Address the customer by name if they share it

### Conversation Summary
When the conversation ends (customer says bye, done, or asks for summary), produce:
```json
{{
  "summary": {{
    "customer_intent": "<what they wanted>",
    "qualification": {{
      "treatment_interest": "<service or unknown>",
      "experience_level": "<first-time or returning or unknown>",
      "preferred_timing": "<timing or unknown>"
    }},
    "sop_gaps": ["<any questions you could not answer>"],
    "escalation_triggered": <true|false>,
    "escalation_reason": "<reason or null>",
    "recommended_next_action": "<e.g. Book a free consultation via WhatsApp>"
  }}
}}
```
Then add a brief warm closing message.
"""

# ── Escalation Check (local keyword scan as first-pass) ──────────────────────

def local_escalation_check(user_message: str) -> str | None:
    """Quick keyword scan before sending to the model."""
    lower = user_message.lower()
    for kw in ESCALATION_KEYWORDS:
        if kw in lower:
            return kw
    return None

# ── Anthropic Client ──────────────────────────────────────────────────────────

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

# ── Conversation Engine ───────────────────────────────────────────────────────

def chat(messages: list, system: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return response.content[0].text

# ── Escalation Logger ─────────────────────────────────────────────────────────

def log_escalation(reason: str, sentiment: str, transcript: list):
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_entry = {
        "timestamp": timestamp,
        "escalation_reason": reason,
        "sentiment": sentiment,
        "transcript_length": len(transcript),
    }
    path = os.path.join(LOG_DIR, f"escalation_{timestamp}.json")
    with open(path, "w") as f:
        json.dump(log_entry, f, indent=2)
    print(f"\n  [LOG] Escalation logged → {path}")

# ── Parse Escalation from Model Response ─────────────────────────────────────

def parse_escalation(response_text: str) -> dict | None:
    """Extract ESCALATE JSON block from model response if present."""
    import re
    pattern = r"```json\s*(\{.*?\"action\"\s*:\s*\"ESCALATE\".*?\})\s*```"
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None

# ── Parse Summary from Model Response ────────────────────────────────────────

def parse_summary(response_text: str) -> dict | None:
    import re
    pattern = r"```json\s*(\{.*?\"summary\".*?\})\s*```"
    match = re.search(pattern, response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None

# ── Main Conversation Loop ────────────────────────────────────────────────────

def run():
    sop_text   = load_sop(SOP_PATH)
    system     = build_system_prompt(sop_text)
    messages   = []
    escalated  = False
    unanswered = 0

    print("=" * 60)
    print("  Bloom Aesthetics Clinic — AI Support (powered by Claude)")
    print("  Type 'quit', 'bye', or 'summary' to end the session.")
    print("=" * 60)
    print()

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue

        end_keywords = ["quit", "bye", "goodbye", "done", "summary", "end"]
        session_ending = any(kw in user_input.lower() for kw in end_keywords)

        # ── Local escalation check ────────────────────────────────────────────
        if not escalated:
            triggered_kw = local_escalation_check(user_input)
            if triggered_kw:
                print(f"\n  [ESCALATION DETECTED — keyword: '{triggered_kw}']\n")

        # ── Add to history & get model response ──────────────────────────────
        messages.append({"role": "user", "content": user_input})
        reply = chat(messages, system)
        messages.append({"role": "assistant", "content": reply})

        # ── Check if model triggered escalation ──────────────────────────────
        escalation_data = parse_escalation(reply)
        if escalation_data and not escalated:
            escalated = True
            log_escalation(
                reason    = escalation_data.get("reason", "unknown"),
                sentiment = escalation_data.get("sentiment", "unknown"),
                transcript= messages,
            )
            # Strip the JSON block from the printed reply for readability
            clean_reply = reply.replace(
                reply[reply.find("```json"):reply.rfind("```") + 3], ""
            ).strip()
            print(f"\nBloom: {clean_reply}\n")
            print("  ─── Human agent handoff initiated. Session continuing for summary. ───\n")
            continue

        # ── Check for summary trigger ─────────────────────────────────────────
        summary_data = parse_summary(reply)
        if summary_data or session_ending:
            clean_reply = reply
            if summary_data:
                clean_reply = reply.replace(
                    reply[reply.find("```json"):reply.rfind("```") + 3], ""
                ).strip()
                print(f"\nBloom: {clean_reply}")
                print("\n" + "=" * 60)
                print("  SESSION SUMMARY")
                print("=" * 60)
                print(json.dumps(summary_data, indent=2))
            else:
                print(f"\nBloom: {reply}\n")
            print("\n  Session ended. Goodbye!\n")
            break

        print(f"\nBloom: {reply}\n")


if __name__ == "__main__":
    run()
