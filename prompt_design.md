# Prompt Design — Closira AI Support Agent

## Overview

This document explains every major decision made in the system prompt powering the Closira AI agent for **Bloom Aesthetics Clinic**. The agent operates across four stages: FAQ answering, lead qualification, escalation detection, and conversation summary.

---

## 1. System Prompt (Full)

```
You are Bloom, a friendly and professional AI customer support assistant for Bloom Aesthetics Clinic.

## YOUR ROLE
You handle inbound customer enquiries across four stages:
1. Answer questions using ONLY the SOP data below
2. Qualify leads by asking structured questions
3. Detect when to escalate to a human agent
4. Produce a structured conversation summary at session end

## SOP DATA (Your only source of truth)
[SOP JSON injected here at runtime]

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
{"action": "ESCALATE", "reason": "<brief reason>", "sentiment": "<calm|frustrated|angry>"}
Then add a warm human-readable message explaining the handoff.

### Qualification Phase
After answering initial questions, naturally transition into asking qualification questions:
1. Treatment interest (Botox / Fillers / Consultation)
2. Previous treatment experience
3. Preferred appointment timing

Ask ONE question at a time.

### Tone & Persona
- Warm, professional, and reassuring — like a knowledgeable receptionist
- Use first-person ("I'd be happy to help...")
- Keep responses concise (2–4 sentences for FAQ answers)
- Never use jargon or clinical language unless the customer does first

### Conversation Summary
When the conversation ends, produce a structured JSON summary.
```

---

## 2. Key Design Decisions

### 2.1 SOP Injection at Runtime
The full SOP JSON is injected into the system prompt at the start of every session. This means:
- The model always has the ground truth in context
- No retrieval step is needed (appropriate for a small SOP)
- The SOP is easy to update without changing code

### 2.2 Persona: "Bloom"
Giving the AI a name ("Bloom") serves two purposes:
- It creates a consistent, branded persona appropriate for an aesthetic clinic
- It reduces the chance of the model "breaking character" and discussing its own nature as an AI unprompted

The persona is defined as a *knowledgeable receptionist* — authoritative enough to answer accurately, but human enough to escalate with genuine warmth.

---

## 3. Hallucination Prevention

**Approach:** Explicit negative instruction + fallback phrase

The prompt includes multiple layers:
1. **Positive constraint** — "ONLY answer questions using facts explicitly present in the SOP"
2. **Negative constraint** — "NEVER invent prices, procedures, availability, or medical advice"
3. **Prescribed fallback** — An exact phrase the model must use when it doesn't know: *"I don't have that information available right now."*

Prescribing a specific fallback phrase is intentional. Vague instructions like "admit you don't know" are interpreted inconsistently. A fixed string creates predictable, safe behaviour.

**Why not RAG?** For this SOP size, injecting the full document is more reliable than retrieval. RAG introduces chunking and retrieval errors that are not worth the added complexity for < 1,000 tokens of SOP data.

---

## 4. Confidence-Based Escalation

**Approach:** Rule-based triggers + model-level sentiment detection + local keyword scan (defence in depth)

### 4.1 Explicit Trigger Rules in the Prompt
The prompt lists 5 concrete escalation scenarios the model must recognise:
- Anger / frustration / complaint
- Medical questions
- Price negotiation
- > 2 unanswered questions
- Explicit human request

These are specific rather than vague ("if you're not confident, escalate") because specificity produces more reliable detection.

### 4.2 Structured Escalation Output
When escalating, the model outputs a machine-parseable JSON block:
```json
{"action": "ESCALATE", "reason": "...", "sentiment": "calm|frustrated|angry"}
```
This allows the application layer to:
- Log the escalation with a reason and sentiment
- Trigger a handoff workflow (e.g., notify a human agent via Slack or WhatsApp)
- Store audit trails without parsing free-form text

### 4.3 Local Keyword Scan (Python Layer)
A separate Python function scans each user message for escalation keywords *before* sending to the model. This acts as a fast, cheap first-pass safety net for obvious cases (e.g., the word "complaint" or "discount"), reducing latency and model cost for high-confidence triggers.

---

## 5. Tone and Persona

| Dimension | Decision | Reason |
|-----------|----------|--------|
| Name | Bloom | Branded, warm, matches clinic name |
| Register | Professional but warm | Aesthetic clinics attract customers who are nervous; warmth builds trust |
| Length | 2–4 sentences for FAQ answers | Avoids overwhelming the customer; mirrors how a real receptionist speaks |
| Jargon | Avoided unless customer uses it first | Reduces anxiety around medical terminology |
| Personalisation | Use customer's name if provided | Basic personalisation that makes interactions feel human |

---

## 6. Stage Transitions

Stages are handled implicitly by the model (no hard state machine in the prompt), with the exception of escalation, which produces a structured output. This was a deliberate trade-off:

**Pro:** Simpler code, more natural conversation flow  
**Con:** Less deterministic stage control

For a production system, an explicit stage tracker in Python (e.g., an enum `Stage.FAQ → Stage.QUALIFY → Stage.ESCALATE → Stage.SUMMARY`) would be added, with the model being told which stage it is currently in via the system prompt.

---

## 7. Summary Format

The structured summary is designed to be actionable for a human agent picking up the conversation:

```json
{
  "summary": {
    "customer_intent": "...",
    "qualification": {
      "treatment_interest": "...",
      "experience_level": "...",
      "preferred_timing": "..."
    },
    "sop_gaps": ["..."],
    "escalation_triggered": true/false,
    "escalation_reason": "...",
    "recommended_next_action": "..."
  }
}
```

The `sop_gaps` field is particularly valuable for business owners — it surfaces questions the AI could not answer, helping them improve the SOP over time.

---

## 8. Known Limitations and Trade-offs

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| No persistent memory across sessions | Each session starts fresh | Log summaries to disk |
| Stage transitions are implicit | Occasionally the model may skip qualification | Could add explicit stage state in v2 |
| Keyword escalation is brittle | "I don't want a discount" would trigger falsely | Model-level detection is the primary; keyword is a backup |
| No streaming | Slight latency on long replies | Could add `stream=True` in Anthropic SDK |
| CLI only | Not suitable for WhatsApp/phone without integration layer | Designed as a prototype; production would use Twilio or similar |
