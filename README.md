# Closira AI Support Agent

An AI-powered customer support workflow for **Bloom Aesthetics Clinic**, built with Python and the Anthropic Claude API. This is an internship assignment submission demonstrating prompt engineering, multi-stage agentic logic, escalation detection, and structured conversation summaries.

---

## Project Structure

```
closira-agent/
├── main.py                          # Main conversation loop
├── sop.json                         # SOP data for Bloom Aesthetics Clinic
├── prompt_design.md                 # Full prompt design document
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
└── test_transcripts/
    ├── 01_in_sop_question.md        # In-SOP FAQ (Botox prices)
    ├── 02_out_of_scope.md           # Out-of-scope question handling
    ├── 03_escalation_trigger.md     # Angry customer / complaint
    ├── 04_lead_qualification.md     # Lead qualification flow
    └── 05_conversation_summary.md   # Full session with summary
```

---

## The Four Stages

| Stage | What It Does |
|-------|-------------|
| 1 — FAQ Answering | Answers customer questions using **only** the SOP JSON. Never hallucinates. |
| 2 — Lead Qualification | Asks 3 structured questions: treatment interest, experience level, timing preference. |
| 3 — Escalation Detection | Detects complaints, medical questions, price negotiation, sentiment, or out-of-scope questions. Logs to `logs/`. |
| 4 — Conversation Summary | On session end, produces a structured JSON summary with intent, qualification data, SOP gaps, and next action. |

---

## SOP Data

The agent operates from `sop.json`, which contains:
- **Business:** Bloom Aesthetics Clinic
- **Hours:** Monday–Saturday, 9am–7pm
- **Services:** Botox (from £200), Dermal Fillers (from £250), Free Consultations
- **Booking:** Via WhatsApp or website. 24-hour cancellation policy.
- **Escalation rules:** Complaints, medical questions, pricing negotiation, > 2 unanswered questions, explicit human request

---

## Setup

### Requirements
- Python 3.10 or higher
- An [Anthropic API key](https://console.anthropic.com)

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/closira-agent.git
cd closira-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your API key
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```
On Windows:
```bash
set ANTHROPIC_API_KEY=your-api-key-here
```

### 4. Run the agent
```bash
python main.py
```

---

## How to Use

- Type your message and press **Enter**
- The agent will respond as Bloom, the clinic's AI assistant
- Type `summary`, `bye`, or `quit` to end the session and generate a summary
- Escalation logs are saved to the `logs/` directory automatically

---

## Example Interaction

```
You: What are your Botox prices?

Bloom: Our Botox treatments start from £200. The exact price will depend 
on the areas being treated, which we'd assess during your free consultation...
```

---

## Dependencies

```
anthropic>=0.28.0
```

---

## Trade-offs and Known Limitations

| Limitation | Notes |
|------------|-------|
| No persistent memory | Each session is independent. Summaries are printed to stdout; save them manually or extend with file logging. |
| CLI only | No WhatsApp/web integration. This is a prototype — production would use Twilio or a webhook handler. |
| Stage transitions are implicit | The model manages stage flow via the system prompt rather than an explicit state machine. This is slightly less deterministic but keeps the code simple. |
| Keyword escalation is naive | The local keyword scan can trigger on negations (e.g. "I don't want a discount"). The model-level detection is the primary mechanism; the keyword scan is a fast backup. |
| Single model call per turn | No streaming. Responses may take 1–2 seconds. Add `stream=True` in the Anthropic SDK call for production. |

---

## Prompt Design

See [`prompt_design.md`](./prompt_design.md) for the full system prompt, hallucination prevention strategy, escalation logic, and tone decisions.

---

## Test Transcripts

Five sample conversations covering every required scenario are in [`test_transcripts/`](./test_transcripts/).

---

## Author

Built as part of the Closira AI Engineering Intern assignment.
