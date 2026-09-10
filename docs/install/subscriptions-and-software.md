# Subscriptions & Software - Complete List

Everything you need for your AI Business Assistant, listed by priority with exact links.

---

## Must Have - Required to Run Today

| Tool | Cost | What It Is | Get It |
|---|---|---|---|
| **Claude Max** | $100 USD/mo | The AI brain - powers everything | [claude.ai](https://claude.ai) → Settings → Billing |
| **Claude Desktop** | Free | The app where you chat with your assistant, open project folders, and run commands | [claude.ai/download](https://claude.ai/download) |
| **Node.js LTS** | Free | Required for some connectors | [nodejs.org](https://nodejs.org) (auto-installed on Mac) |
| **Git** | Free | Downloads the workshop kit | Auto-installed on Mac via Xcode tools |
| **GitHub Account** | Free | Where the workshop kit is stored | [github.com/signup](https://github.com/signup) |

**Required monthly cost: $100 USD (~$155 AUD/month)**

---

## Free Accounts - Set Up Before the Workshop

| Account | What It Gives You | Get It |
|---|---|---|
| **Google Account (Gmail)** | Gmail + Calendar + Drive - connects to your assistant | [accounts.google.com/signup](https://accounts.google.com/signup) |
| **GitHub** | Download the workshop kit | [github.com/signup](https://github.com/signup) |
| **Telegram** | Phone notifications from your assistant | [telegram.org](https://telegram.org) (install on phone) |
| **iMessage** (Mac only) | Text your assistant from iPhone - no extra app | Built into macOS (free) |

**Total: Free**

---

## Recommended Connections - Add After the Workshop

These connect to Claude Code with one command (or a short setup walkthrough). No extra cost unless noted.

| Tool | Cost | What Your Assistant Can Do | Connect With |
|---|---|---|---|
| **Google Workspace** | Free (Google account) | Gmail, Calendar, Drive, Docs, Sheets, and more | `npm install -g @googleworkspace/cli` then `gws auth login` |
| **Telegram Bot** | Free | Message your assistant from your phone | Ask your assistant: `Connect Telegram` |
| **iMessage** (Mac only) | Free | Text your assistant from iPhone/Mac | Ask your assistant: `Connect iMessage` |
| **Notion** | Free / $10 USD/mo | Read and update your notes and workspace | Ask your assistant: `Connect Notion` |
| **GitHub** | Free | Read repos, issues, pull requests, CI status | Ask your assistant: `Connect GitHub` |
| **HubSpot** | Free / paid tiers | Read and update contacts, deals, companies, notes | Ask your assistant: `Connect HubSpot` |
| **Square** | Free | Read payments, orders, customers, invoices | Ask your assistant: `Connect Square` |
| **CircleCI** | Free tier | Check build status, read logs, trigger reruns | Ask your assistant: `Connect CircleCI` |

---

## Optional Upgrades - For When You're Ready

Not needed today. Come back to these once your assistant is running well.

| Tool | Cost | What It Does |
|---|---|---|
| **GoHighLevel (GHL)** | $97-297 USD/mo | All-in-one CRM - contacts, pipeline, marketing, messaging | [gohighlevel.com](https://www.gohighlevel.com) |
| **n8n** | $24 USD/mo | Visual automation - run tasks in the background 24/7 | [n8n.io](https://n8n.io) |
| **Make (Integromat)** | Free-$16 USD/mo | Connect apps and automate workflows | [make.com](https://make.com) |
| **Zapier** | $20-$69 USD/mo | Similar to Make - simpler but more expensive | [zapier.com](https://zapier.com) |

---

## Always-On Server - For Work That Must Listen Non-Stop

Most recurring work does not need a server. Anything that wakes up, runs, and stops - sending follow-ups, lead digests, processing invoices - runs as a cloud routine instead, which needs no server and keeps working while your laptop is off. Just ask your assistant for it; when the task uses apps and sign-ins set up on your computer, it packages those up for you with `/package-as-routine`.

A server earns its cost only when a task must listen non-stop: reply within seconds, hold a live connection open (a Telegram or WhatsApp bot), or be reachable from the internet so other services can call it.

> **Check before you buy:** [automation-loop-and-schedule.md - section 7](../extend/automation-loop-and-schedule.md#7-always-on-server---continuous-listeners) has a four-question test. If every answer is no, a routine does the job and you can skip this section.

| Option | Cost | Notes |
|---|---|---|
| **AWS Lightsail** | $10 USD/mo | Luke's recommendation - simple and reliable |
| **DigitalOcean Droplet** | $6-12 USD/mo | Great documentation for beginners |
| **Hetzner VPS** | $4-8 USD/mo | Cheapest option |
| **Vultr** | $6-12 USD/mo | Good performance |

**To set up a server yourself:**
1. Create an account on your chosen provider (links above)
2. Spin up the smallest Linux instance (Ubuntu 22.04)
3. Tell your assistant: "Help me set up Claude Code on my new server - here are the SSH details: [paste your server IP and login]"
4. Your assistant will walk you through the rest step by step

> Need help? Ask your assistant to guide you through it.

---

## Windows Users - Extra Required Software

| Tool | Cost | What It Is | Get It |
|---|---|---|---|
| **Git for Windows** | Free | Provides Git, used by the install and update steps behind the scenes | [git-scm.com/downloads/win](https://git-scm.com/downloads/win) |

---

## Full Cost Summary

| What | AUD/month (approx) |
|---|---|
| Claude Max (required) | ~$155 |
| Server - AWS Lightsail (optional) | ~$15 |
| GoHighLevel CRM (optional) | ~$150-450 |
| n8n automation (optional) | ~$37 |
| **Minimum to get started** | **~$155/month** |
| **Full recommended stack** | **~$200-250/month** |

---

## What $155/Month Gets You

- An AI assistant available 24/7 - never sick, never on leave, never distracted
- Writes, researches, and automates across your whole business
- <!-- skills-audit:total -->208<!-- /skills-audit:total --> specialist skills built in from day one
- Gets smarter every time you use it
- Replaces 10-20 hours of admin and content work per month

---

*Claude Code Workshop - selrai.com.au*
