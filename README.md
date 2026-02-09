<p align="center">
  <img src="demo-video/thumbnail_yt.png" alt="Gemini GrowLab" width="800"/>
</p>

<h1 align="center">Gemini GrowLab</h1>

<p align="center">
  <strong>An autonomous AI-powered grow tent that uses Google Gemini's multimodal intelligence to grow basil from seed — zero human intervention.</strong>
</p>

<p align="center">
  <a href="#demo">Demo</a> &bull;
  <a href="#how-it-works">How It Works</a> &bull;
  <a href="#architecture">Architecture</a> &bull;
  <a href="#hardware">Hardware</a> &bull;
  <a href="#setup">Setup</a> &bull;
  <a href="#dashboard">Dashboard</a> &bull;
  <a href="#lessons-learned">Lessons Learned</a>
</p>

---

## The Idea

Growing plants hydroponically is surprisingly hard. pH drifts, humidity swings, and nutrient imbalances can kill a seedling overnight — and the "optimal" response depends on multiple interacting variables at once. We realized that Gemini's multimodal capabilities (vision + structured reasoning) could act as an always-on agronomist: one that **sees** the plant, **reads** the numbers, **remembers** what it did last time, and makes calibrated decisions — every single hour, without fatigue or guesswork.

**The goal was simple: drop a basil seed into a hydroponic bucket, close the tent, and let the AI figure out the rest.**

---

## Demo

<p align="center">
  <a href="https://youtu.be/wMVxyqbZxvE">
    <img src="demo-video/thumbnail_yt.png" alt="Watch Demo Video" width="600"/>
  </a>
  <br/>
  <em>Click to watch the full demo video</em>
</p>

---

## How It Works

A Raspberry Pi inside a grow tent runs a **9-step control loop every 60 minutes** via cron:

```
Sensors → CSV Storage → Camera → Load History → Gemini AI → Store Decision → Execute Actions → Log Reasoning → Stream Video
```

| Step | What Happens |
|------|-------------|
| **1. Read Sensors** | 5 sensors sampled 5x each with outlier rejection (discard first 2, average last 3) |
| **2. Store Data** | Append validated readings to CSV for historical trend analysis |
| **3. Capture Photo** | USB webcam photographs the plant under grow lights |
| **4. Load History** | Retrieve the last 3 AI decisions for temporal context |
| **5. Query Gemini** | Send sensor data + photo + history + domain knowledge to Gemini 3 Flash |
| **6. Store & Upload** | Save decision locally and upload to Supabase (PostgreSQL + photo storage) |
| **7. Execute Actions** | Toggle smart plugs (light, air pump, humidifier) and run dosing pumps (pH up/down) |
| **8. Log Reasoning** | Record per-actuator reasoning and check for human intervention flags |
| **9. Stream Video** | Stream 5 minutes of 1080p video to a remote PC for timelapse assembly |

### What Gemini Decides

Every hour, Gemini returns a **structured JSON** with:

```json
{
  "light": "on",
  "air_pump": "on",
  "humidifier": "off",
  "ph_adjustment": "none",
  "reasoning": {
    "overall": "All parameters within ideal ranges...",
    "light_reason": "Currently 2 PM, within the 6AM-10PM light period...",
    "air_pump_reason": "Continuous aeration maintains dissolved oxygen...",
    "humidifier_reason": "Humidity at 58%, well within 40-70% range...",
    "ph_reason": "pH at 6.1, within ideal 3.5-6.5 range..."
  },
  "plant_health_score": 8,
  "human_intervention": {
    "needed": false,
    "message": ""
  }
}
```

The AI explains **every** decision it makes. No black box.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GROW TENT                                   │
│                                                                     │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│   │  DHT22   │  │ DS18B20  │  │ pH Probe │  │TDS Probe │          │
│   │ Air/Hum  │  │  Water   │  │ (Analog) │  │ (Analog) │          │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│        │              │             │              │                 │
│        │     GPIO     │   1-Wire    │    ┌─────────┘                │
│        │              │             │    │  Signal                   │
│        │              │             │    │  Isolator                 │
│        │              │             ▼    ▼                           │
│   ┌────┴──────────────┴──────── ADS1115 ADC ──────┐                │
│   │                                                │                │
│   │              RASPBERRY PI 3                    │                │
│   │                                                │                │
│   │    main.py (9-step control loop, cron)         │                │
│   │    gemini_client.py (Gemini 3 Flash API)       │                │
│   │    sensors.py / actuators.py / camera.py       │                │
│   │                                                │                │
│   └───────────┬──────────┬──────────┬──────────────┘                │
│               │          │          │                                │
│         ┌─────┘    ┌─────┘    ┌─────┘                               │
│         ▼          ▼          ▼                                      │
│   ┌──────────┐ ┌────────┐ ┌────────────┐  ┌──────────────────┐     │
│   │Tuya Smart│ │Dosing  │ │ USB Webcam │  │ VIPARSPECTRA     │     │
│   │Power     │ │Pumps   │ │  (1080p)   │  │ P1000 LED Light  │     │
│   │Strip     │ │pH+/pH- │ └────────────┘  └──────────────────┘     │
│   │(3 plugs) │ │(12V)   │                                          │
│   └──────────┘ └────────┘                                           │
│    Light │ Air Pump │ Humidifier                                    │
└─────────┼──────────┼────────────────────────────────────────────────┘
          │          │
          ▼          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         CLOUD                                       │
│                                                                     │
│   ┌──────────────────────┐       ┌──────────────────────┐          │
│   │      SUPABASE        │       │       VERCEL          │          │
│   │  ┌────────────────┐  │       │  ┌────────────────┐  │          │
│   │  │  PostgreSQL DB  │  │◄──────│  │ Next.js 16     │  │          │
│   │  │  (decisions)    │  │  ISR  │  │ Dashboard      │  │          │
│   │  ├────────────────┤  │  60s  │  │ (React 19)     │  │          │
│   │  │  Storage Bucket │  │       │  └────────────────┘  │          │
│   │  │  (plant-photos) │  │       │                      │          │
│   │  └────────────────┘  │       │  Public URL →         │          │
│   │  RLS: read-only pub  │       │  Anyone can watch     │          │
│   └──────────────────────┘       │  the basil grow       │          │
│                                  └──────────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Hardware

### Full Bill of Materials

| Category | Component | Purpose |
|----------|-----------|---------|
| **Compute** | Raspberry Pi 3 | Brain — runs the control loop, Gemini API calls, sensor reads |
| **Environment** | 24"x24"x48" Grow Tent | Controlled growing environment |
| **Lighting** | VIPARSPECTRA P1000 LED | Full-spectrum grow light (100W, dimmable) |
| **Hydroponics** | VIVOSUN 5-gal DWC Kit | Deep Water Culture bucket with air stone |
| **Sensor** | DHT22 | Air temperature + humidity |
| **Sensor** | DS18B20 (waterproof) | Water temperature (1-Wire) |
| **Sensor** | DFRobot Gravity pH Sensor V2 | Water acidity (analog) |
| **Sensor** | DFRobot Gravity TDS Sensor | Nutrient concentration (analog) |
| **ADC** | ADS1115 16-bit | Converts analog sensor signals to digital (I2C) |
| **Isolation** | DFRobot Signal Isolator | Prevents pH/TDS electrical cross-talk |
| **Actuator** | Tuya WP9 Smart Power Strip | 3 independently controlled outlets (LAN control) |
| **Actuator** | 2x Peristaltic Dosing Pumps (12V) | pH Up and pH Down dosing |
| **Motor Driver** | TB6612FNG | Dual H-bridge for dosing pump control |
| **Camera** | USB Webcam (1080p) | Plant photography + video streaming |
| **Other** | Air pump, humidifier, tubing, wires | Supporting equipment |

### Wiring Architecture

```
                    ┌─────────────┐
pH Probe ──────────►│             │
                    │   ADS1115   │◄──── I2C ────► Raspberry Pi
                    │   (ADC)     │
TDS Probe ─► [Signal Isolator] ─►│             │
                    └─────────────┘
```

The signal isolator is **critical** — without it, the pH and TDS probes in the same reservoir create galvanic interference that corrupts both readings.

---

## The AI Layer

### Prompt Engineering for Physical Systems

The Gemini prompt is not a simple "what should I do?" — it encodes **domain expertise**:

- **Temporal context**: Current time, light schedule (16h on / 8h off), and whether it's currently day or night
- **Ideal ranges**: Basil-specific DWC parameters (pH 3.5–6.5, TDS 100–840 ppm, air temp 20–28°C, etc.)
- **Safety guardrails**: "Only dose pH if >0.5 outside ideal range" — prevents oscillation from over-correction
- **Cross-variable reasoning**: "Light affects temperature" — the AI considers second-order effects
- **History**: Last 3 decisions with full reasoning, so the AI can evaluate whether past actions worked
- **Visual input**: Live plant photo for health assessment

### Structured Output

Gemini's response is forced into a **strict JSON schema** via `response_mime_type: application/json` with a defined `response_schema`. Every field is typed and validated — no parsing ambiguity, no hallucinated formats.

### Safe Fallback

If the Gemini API fails, the system doesn't crash or freeze. It falls back to **safe defaults** (light on, air pump on, humidifier off, no pH dosing) and raises a human intervention flag.

---

## Dashboard

A public **Next.js dashboard** on Vercel displays real-time data from the grow tent:

- **Sensor readings** with color-coded status (green/yellow/red)
- **Live plant photo** uploaded from the Pi every hour
- **AI decision breakdown** — what each actuator is doing and why
- **Plant health score** (0–10) assessed by Gemini from sensor data + visual inspection
- **Intervention alerts** — red banner when the AI thinks a human should check in

The dashboard uses **ISR (Incremental Static Regeneration)** with 60-second revalidation — the page auto-updates without hammering the database.

> See the dashboard README: [`hydroponics-dashboard/README.md`](hydroponics-dashboard/README.md)

---

## Project Structure

```
Gemini-hydroponics/
├── main.py                  # 9-step control loop (cron entry point)
├── config.py                # All constants, pins, thresholds, paths
├── sensors.py               # DHT22, DS18B20, pH, TDS — multi-read averaging
├── actuators.py             # Tuya smart plugs + dosing pumps
├── camera.py                # USB webcam photo capture
├── gemini_client.py         # Prompt builder + Gemini API + JSON parsing
├── data_store.py            # CSV/JSON persistence layer
├── supabase_uploader.py     # Cloud upload (decisions + photos)
├── video_streamer.py        # 1080p video streaming to remote PC
├── dashboard.py             # Local HTML report generator (matplotlib)
├── backfill_decisions.py    # One-time script to sync local → Supabase
├── verify_supabase.py       # Supabase setup verification tests
├── supabase_schema.sql      # Database schema + RLS policies
├── requirements.txt         # Python dependencies
├── data/                    # Local sensor logs, decisions, photos
├── hydroponics-dashboard/   # Next.js cloud dashboard (deployed to Vercel)
└── Individual_Tasks/        # Step-by-step setup documentation
```

---

## Setup

### Prerequisites

- Raspberry Pi 3 (or newer) with Raspberry Pi OS
- Python 3.9+
- Google Cloud project with Vertex AI / Gemini API enabled
- Supabase project (free tier)
- Hardware components (see [BOM](#hardware))

### 1. Clone & Install

```bash
git clone https://github.com/abhijeetvichare76/gemini-growlab.git
cd gemini-growlab
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Google Cloud / Gemini
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=global
GOOGLE_APPLICATION_CREDENTIALS=your-service-account.json

# Supabase
SUPABASE_PROJECT_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=your-publishable-key
SUPABASE_SECRET_KEY=your-secret-key
```

### 3. Set Up Supabase

```bash
# Apply the schema (decisions table + RLS + storage bucket)
psql "postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres" -f supabase_schema.sql

# Verify setup
python verify_supabase.py
```

### 4. Wire the Hardware

Follow the wiring diagram in [`Hydroponics_Complete_BOM.md`](Hydroponics_Complete_BOM.md). Key connections:
- DHT22 → GPIO 17
- DS18B20 → GPIO 4 (1-Wire)
- pH → ADS1115 Channel 1
- TDS → Signal Isolator → ADS1115 Channel 0
- Dosing pumps → TB6612FNG → Pi I2C

### 5. Schedule the Cron Job

```bash
crontab -e
# Add:
*/60 * * * * cd /path/to/Gemini-hydroponics && venv/bin/python main.py
```

### 6. Deploy the Dashboard

```bash
cd hydroponics-dashboard
npm install
npm run build
vercel --prod
```

---

## Challenges & Lessons Learned

### Soldering Disaster
First time soldering — applied too much heat to the ADS1115 ADC and fried it completely. Ordered a replacement, started over. No amount of YouTube tutorials fully prepares you for the real thing.

### Sensor Cross-Talk
pH and TDS probes in the same reservoir interfere electrically. Solved with a **galvanic signal isolator** on the TDS line and a multi-read averaging strategy (5 reads, discard first 2 unstable ones, average the rest).

### Humidifier Caused Fungal Infection
Running the humidifier continuously between hourly readings pushed humidity to ~80%, causing fungal spots on basil leaves. Now runs in **5-minute bursts** with auto-shutoff baked into the control loop.

### pH Safety
Bad pH readings could cause Gemini to over-dose acid/base, killing the plant. Added hard validation bounds (3.0–9.0), default-to-neutral logic, and prompt-level instructions for conservative dosing only when pH drifts >0.5 outside ideal range.

### Prompt Engineering for Physical Systems
When your AI controls real actuators, you need guardrails in the prompt: conservative dosing rules, temporal context, explicit "never do X when Y" constraints. A hallucinated pH adjustment can kill a plant.

---

## Built With

| Layer | Technology |
|-------|-----------|
| **AI** | Google Gemini 3 Flash (Vertex AI) — multimodal vision + structured JSON output |
| **Hardware** | Raspberry Pi 3, DHT22, DS18B20, ADS1115, DFRobot pH/TDS, TB6612FNG, Tuya WP9 |
| **Backend** | Python — sensor drivers (Adafruit CircuitPython), TinyTuya (LAN), OpenCV |
| **Database** | Supabase (PostgreSQL + Storage, RLS-secured) |
| **Frontend** | Next.js 16, React 19, Tailwind CSS 4, TypeScript |
| **Hosting** | Vercel (ISR with 60s revalidation) |
| **Protocols** | Tuya v3.3 (encrypted LAN), I2C, 1-Wire, GPIO |

---

## What's Next

- **Light intensity control** — VIPARSPECTRA P1000 supports dimming; add PWM for AI-controlled brightness
- **Full nutrient dosing** — Peristaltic pumps for FloraMicro/FloraGrow/FloraBloom
- **Gemini long-context** — Feed weeks of growth data + photos for trend-aware decisions
- **Push notifications** — Email/SMS alerts when the intervention flag fires
- **Multi-plant support** — Independent AI profiles per grow tent/bucket
- **Community templates** — Pluggable plant profiles (tomatoes, lettuce, herbs) with custom ideal ranges

---

<p align="center">
  <strong>Built for the Google Gemini API Developer Competition</strong>
  <br/>
  <em>Growing basil in -19°C Jersey winter, powered entirely by AI.</em>
</p>
