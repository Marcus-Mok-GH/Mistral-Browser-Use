# Mistral Browser Use (MBU)

Mistral Browser Use is a simple project for people who want an easier way to explore the web with AI-style help on mobile devices. In this README, **MBU** is just a short name for **Mistral Browser Use**.

Instead of feeling locked into heavy browser automation tools, this project focuses on a lighter idea: ask for what you need, and let Mistral Browser Use (MBU) help search and navigate using the Mistral API.

---

## What this project is

MBU is a small, practical experiment that:

- Connects to the **Mistral free API**.
- Helps perform web-search style tasks.
- Is aimed at people who want a more straightforward experience, especially on mobile.

If you have ever felt that browser automation tools were too complex, MBU is meant to feel friendlier and more direct.

---

## Why MBU exists

Many web-automation projects are powerful, but they can be difficult for casual use.

MBU was created with a simpler goal:

- Make web exploration feel approachable.
- Reduce setup friction.
- Give users a quick way to try AI-assisted browsing ideas.

This project is a good fit for learners, tinkerers, and anyone curious about lightweight AI-powered browsing workflows.

---

## Who this is for

You may like this project if you are:

- A beginner trying AI web tools for the first time.
- A mobile user looking for a simpler workflow.
- A developer who wants a minimal starting point before building bigger features.

---

## What you need

To use MBU, you mainly need one of the following:

- **Mistral AI:** Access to a Mistral account and an API key from the [Mistral Console](https://console.mistral.ai/).
- **Fireworks (Kimi K2.6):** A built-in provider that doesn't require a personal API key.

---

## Usage Limits

To ensure fair usage, MBU includes a request limit:

- **Weekly Limit:** 20 requests per week.
- **Renewal:** If you hit the limit, you can use the renewal code `2026CODERENEWAL` in the chat panel to reset your counter instantly.

---

## Current status

This project is intentionally lightweight and early-stage.

Think of it as a foundation you can use, test, and extend rather than a complete, polished platform.

---

## In plain words

MBU is about making AI-assisted web use feel easier.

It keeps the idea simple:

1. Connect to Mistral.
2. Ask for web help.
3. Get results in a way that is easier to use on mobile and for everyday experimentation.

---

## Notes

- This project uses the Mistral free API.
- You can learn more and manage your account here:  
  https://console.mistral.ai/

If you want, future updates can add clearer setup steps, example use-cases, and screenshots so new users can get started even faster.

## Streamlit deployment note (important)

If you deploy on **Streamlit Community Cloud**, Python version is selected in the app's **Advanced settings** (or app settings dashboard).

- `runtime.txt` is **not** used by Community Cloud to pick Python.
- Set Python explicitly in deployment settings (recommended: **Python 3.12 or 3.14+** for this app).
- MBU includes automatic compatibility handling for Python 3.14 import edge-cases via the `_import_local_symbol()` function in app.py, so both 3.12 and 3.14+ should work seamlessly.
- If you experience any import issues, try switching between Python versions in the deployment settings and redeploying.

