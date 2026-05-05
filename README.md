# ☎️ Asterisk AI Info Line

An AI-powered phone info line that answers callers' questions in real-time using OpenAI's Whisper (speech-to-text) and GPT-4o (response + TTS). Built with Asterisk PBX + Python + Docker.

---

## How it works

![image](https://github.com/user-attachments/assets/9f2f149d-65f0-419c-8bfe-a1bc6e8f283f)

1. A call arrives via Twilio SIP trunk into Asterisk
2. Asterisk streams the audio to the Python bridge via AGI
3. Python sends audio to OpenAI Whisper for transcription
4. GPT-4o generates a spoken response
5. OpenAI TTS converts the response to audio, played back to the caller
6. Full transcript + call metadata is saved to SQLite

---

## Requirements

- Docker & Docker Compose
- A [Twilio account](https://twilio.com) with a SIP trunk
- An [OpenAI API key](https://platform.openai.com)
- A phone number (HU for dev, NZ for production)

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/asterisk-ai-infoline
cd asterisk-ai-infoline
cp .env.example .env
```

Edit `.env` with your credentials (see [Configuration](#configuration) below).

### 2. Start

```bash
docker compose up -d
```

That's it. The system is live and accepting calls.

### 3. Check logs

```bash
docker compose logs -f bridge    # Python bridge logs
docker compose logs -f asterisk  # Asterisk PBX logs
```

---

## Configuration

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token |
| `SIP_TRUNK_HOST` | Twilio SIP trunk hostname |
| `SIP_USERNAME` | SIP credential username |
| `SIP_PASSWORD` | SIP credential password |
| `AI_PERSONA` | System prompt for GPT (customise the AI's role) |
| `MAX_CALL_DURATION` | Max call length in seconds (default: 300) |

---

## Twilio Setup

### Development (Hungarian number)

1. Buy a Hungarian (+36) number in [Twilio Console](https://console.twilio.com)
2. Create an **Elastic SIP Trunk** under `Voice → SIP Trunking`
3. Add origination URI: `sip:YOUR_SERVER_IP:5060`
4. Set the number's voice handler to your SIP trunk

### Production (New Zealand number)

Same process, but:
1. Buy a New Zealand (+64) number
2. Use the **Auckland** region in Twilio for lowest latency
3. Update `SIP_TRUNK_HOST` in `.env` to the NZ-region endpoint

> **Latency tip:** For NZ production, deploy on a Sydney or Auckland cloud server (e.g. DigitalOcean SYD1 region) to keep round-trip audio delay under 150ms.

---

## Call Logs

Transcripts and call metadata are stored in `data/calls.db` (SQLite).

```bash
# View recent calls
docker compose exec bridge python scripts/show_logs.py

# Export to CSV
docker compose exec bridge python scripts/export_csv.py
```

Schema:

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Auto-increment |
| `call_id` | TEXT | Unique call identifier |
| `caller_number` | TEXT | Caller's phone number |
| `started_at` | DATETIME | Call start time |
| `ended_at` | DATETIME | Call end time |
| `duration_seconds` | INTEGER | Total call duration |
| `transcript` | TEXT | Full JSON transcript |
| `summary` | TEXT | GPT-generated call summary |

---

## Customising the AI

Edit `AI_PERSONA` in `.env`:

```env
AI_PERSONA="You are a friendly and professional information line assistant. 
Answer questions clearly and concisely. If you don't know something, say so honestly. 
Keep responses under 3 sentences for telephone clarity."
```

---

## Project Structure

```
asterisk-ai-infoline/
├── docker-compose.yml
├── .env.example
├── README.md
│
├── asterisk/
│   └── conf/
│       ├── sip.conf          # SIP trunk config
│       ├── extensions.conf   # Dialplan (call routing)
│       └── agi-bin/          # AGI scripts (auto-mounted)
│
├── bridge/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py               # AGI entry point
│   ├── openai_handler.py     # Whisper + GPT + TTS
│   ├── database.py           # SQLite logging
│   └── config.py             # Settings loader
│
└── scripts/
    ├── show_logs.py          # CLI log viewer
    └── export_csv.py         # Export transcripts to CSV
```

---

## Deployment (DigitalOcean)

For **development** (Hungary): Frankfurt region (`fra1`) — ~15ms from Budapest  
For **production** (New Zealand): Sydney region (`syd1`) — ~20ms from Auckland

```bash
# One-liner server setup on fresh Ubuntu 22.04
curl -fsSL https://get.docker.com | sh
git clone https://github.com/YOUR_USERNAME/asterisk-ai-infoline
cd asterisk-ai-infoline && cp .env.example .env
# edit .env, then:
docker compose up -d
```

Recommended Droplet: **4GB RAM / 2 vCPU / 80GB SSD** (~$24/month)

---

## License

MIT
