# Claude Code Workshop - AI Business Assistant Kit

**Built by Selr AI - [selrai.com.au](https://selrai.com.au)**

> Give your business an AI assistant that remembers who you are, learns your business, and gets smarter every time you use it - without writing a single line of code.

---

## What Is This?

This kit sets up a personal AI business assistant on your laptop. Not a chatbot you close and forget - an assistant that:

- **Remembers your business** - your name, your customers, your biggest challenges
- **Lives on your computer** - runs locally, not in a browser tab
- **Controls your browser** - can open websites, fill forms, and do research for you
- **Has <!-- skills-audit:total -->208<!-- /skills-audit:total --> specialist skills** - research, copywriting, sales emails, social content, competitor analysis, and more
- **Gets smarter over time** - every conversation builds on the last

It is built on [Claude Code](https://claude.ai/claude-code) by Anthropic - configured specifically for your business.

---

## Read the docs in this order

Everything you need is in [`docs/`](docs/). The reading order:

| Step | Folder | When |
|---|---|---|
| 1 | [`docs/install/`](docs/install/) - what to buy and sign up for | **Before the workshop** |
| 2 | [`docs/start/`](docs/start/) - paste the setup prompt, the one document that installs, updates, or migrates | **During the workshop** |
| 3 | [`docs/use/`](docs/use/) - first prompts, what your assistant remembers, plain-English glossary | **Right after setup** |
| 4 | [`docs/skills/`](docs/skills/) - every skill your assistant can use, grouped by business problem (connecting outside tools is part of Group H) | **Week 1** |
| 5 | [`docs/extend/`](docs/extend/) - optional: VS Code path, scheduling, automation loops | **Month 2+** |
| - | [`docs/troubleshoot.md`](docs/troubleshoot.md) - when something is not working | **Any time** |

If you prefer VS Code over Claude Desktop, see [`docs/extend/vscode.md`](docs/extend/vscode.md) - advanced fallback, not recommended for first-time users.

---

## Quick Start

**Before the workshop**, complete these 2 steps - takes about 10 minutes:

1. Get a **Claude Max** subscription at [claude.ai](https://claude.ai) ($100 USD/month)
2. Install **Claude Desktop** at [claude.ai/download](https://claude.ai/download) and sign in

The kit is downloaded with Git, so Git has to be on the machine. **On Windows, [Git for Windows](https://git-scm.com/download/win) is a real dependency** - the setup prompt installs it for you in its first step if it is missing, and installing it beforehand just makes that step a no-op. On Mac, Git installs itself the first time it is needed.

Everything else (Node.js, Bun, Windows-specific snags) is handled conversationally by your assistant when you paste the setup prompt.

Full pre-workshop details: [`docs/install/`](docs/install/).

---

## At the Workshop

1. Open **Claude Desktop** and start a new Code session - any folder will do, there is nothing to create first
2. Copy the **setup prompt** from the day page at https://loup.academy (the room's password opens it) and paste it into the Code session
3. Claude handles everything - installs what is missing, downloads the kit, copies your skills in, and adds a short managed block to your global `~/.claude/CLAUDE.md` that gives every session your assistant
4. It asks you to quit and reopen Claude Desktop once, part-way through, and tells you exactly when
5. When it finishes, start a new session anywhere and say `hi` - your assistant runs a short orientation, asks about your business, and shows you what it can do

Because the install is global, your assistant works from **every** folder you open - there is no special assistant folder to find your way back to.

Your assistant handles it all conversationally, one step at a time. No scripts to run, no commands to memorise.

Full walkthrough: [`docs/start/setup.md`](docs/start/setup.md).

---

## Common Questions

**Is my data private?**
Yes. Your instructions file (`~/.claude/CLAUDE.md`) and Claude's auto-memory (viewable with `/memory`) live on your computer only. Nothing is sent to a third party except your conversations with Claude (which go to Anthropic, same as using claude.ai normally).

**What does it cost after the workshop?**
Claude Max is $100 USD/month (~$155 AUD). That is the only required cost. Everything else in this kit is free.

**What if I miss a step during setup?**
Paste the same setup prompt again. It works out that you already have an install and picks up where you left off, without trampling anything you have changed since.

**Can I use this on Windows?**
Yes. Just paste the setup prompt - your assistant walks you through everything conversationally, including installing Git for Windows and Node.js and any Windows-specific snags. See [`docs/troubleshoot.md`](docs/troubleshoot.md) if something goes wrong.

---

## Support

- Workshop guides: [`docs/`](docs/)
- Selr AI: [selrai.com.au](https://selrai.com.au)

---

*Claude Code Workshop Kit - Built by Selr AI*
