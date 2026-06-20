# langchain-skim

**Give your LangChain agent the ability to read any URL — clean Markdown, no ads, no nav, no boilerplate. Pays itself per call. No signup, no API key.**

[![PyPI version](https://img.shields.io/pypi/v/langchain-skim.svg)](https://pypi.org/project/langchain-skim/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

`langchain-skim` is the official [LangChain](https://python.langchain.com) tool for [Skim](https://skim402.com) — the canonical [x402](https://x402.org) clean reader API. It exposes one tool, `SkimReader`, that your agent can call to fetch any web page as agent-ready Markdown plus structured metadata (title, byline, published date, language, excerpt). Each call costs **$0.002 in USDC on Base**, paid automatically by your local wallet over HTTP 402.

---

## Install

```bash
pip install langchain-skim
```

This pulls in the x402 client with EVM support, so there's nothing else to install.

---

## Quickstart (60 seconds)

### 1. Fund a Base wallet with $1 of USDC

A dollar funds roughly 500 reads. Full step-by-step (with screenshots, for non-crypto-native devs): **<https://skim402.com/wallet>**.

> **Use a fresh wallet, not your personal one.** This wallet's private key signs payment authorizations on your machine — treat it like a hot wallet for paying $0.002 tolls, not a savings account.

### 2. Point the tool at your wallet

```bash
export SKIM_WALLET_PRIVATE_KEY=0xYOUR_BASE_WALLET_PRIVATE_KEY
```

### 3. Use it

```python
from langchain_skim import SkimReader

reader = SkimReader()  # reads SKIM_WALLET_PRIVATE_KEY from the environment

markdown = reader.invoke({"url": "https://en.wikipedia.org/wiki/HTTP_402"})
print(markdown)
```

The tool signs an EIP-3009 USDC authorization for $0.002, Skim returns clean Markdown, and you get back the article body with a YAML frontmatter block of metadata. The payment shows up in your wallet's transaction history on [BaseScan](https://basescan.org/).

---

## Use it in an agent

`SkimReader` is a standard LangChain `BaseTool`, so it drops straight into any agent's tool list:

```python
from langchain_skim import SkimReader
from langchain.agents import create_react_agent  # or any agent constructor
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")
tools = [SkimReader()]

agent = create_react_agent(llm, tools)
agent.invoke({"messages": [("user", "Read https://example.com/article and summarize it.")]})
```

The agent decides when to call `skim_read`, the wallet pays per read, and the model gets clean Markdown instead of raw HTML.

---

## Output shape

`SkimReader` returns Markdown with a YAML frontmatter block of the page metadata:

```
---
title: Example article
byline: Jane Doe
publishedAt: 2025-01-15
lang: en
excerpt: A short summary...
---

# Example article

The cleaned article body in Markdown...
```

Set `include_metadata=False` to get just the Markdown body.

---

## Configuration

`SkimReader` takes the following parameters (all optional except the wallet key):

| Parameter          | Default                 | Notes                                                                                                                       |
| ------------------ | ----------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `private_key`      | `$SKIM_WALLET_PRIVATE_KEY` | Hex private key for the Base wallet that pays for reads. With or without `0x`. Use a dedicated wallet — never your personal one. |
| `base_url`         | `https://skim402.com`   | Override the API base URL. For self-hosting or local development.                                                          |
| `max_price_usd`    | `0.01`                  | Hard cap on per-call price in USD. The wallet refuses to sign for anything above this. Skim is `$0.002`/call.              |
| `include_metadata` | `True`                  | Prepend a YAML frontmatter block of page metadata to the returned Markdown.                                                |
| `timeout`          | `60`                    | Per-request timeout in seconds.                                                                                            |

```python
reader = SkimReader(
    private_key="0x...",       # or rely on the env var
    max_price_usd=0.005,
    include_metadata=False,
)
```

---

## How it actually works

```
your agent ──► SkimReader ──► POST https://skim402.com/api/v1/read
                  ▲                       │
                  │                       ▼
                  │              402 Payment Required
                  │                  (x402 challenge)
                  │                       │
                  ▼                       │
   x402 signs EIP-3009 USDC ◄─────────────┘
   transfer authorization (locally)
                  │
                  ▼
        retry POST with X-PAYMENT header
                  │
                  ▼
   Skim verifies + settles via Coinbase CDP facilitator
                  │
                  ▼
        200 OK + clean Markdown
```

Your private key never leaves your machine — it only signs authorizations locally.

---

## Security

- **Dedicated wallet, always.** Fund it with only as much USDC as you're willing to spend in a runaway loop. The `max_price_usd` cap catches accidental price escalations.
- **No outbound telemetry from this package.** `langchain-skim` only talks to `skim402.com` (or whatever you set as `base_url`). No analytics, no error reporting, no phone-home.

---

## Try it without an agent

Skeptical? Test the upstream endpoint directly — it'll return a 402 challenge so you can see the protocol in action:

```bash
curl -i -X POST https://skim402.com/api/v1/read \
  -H 'content-type: application/json' \
  -d '{"url":"https://en.wikipedia.org/wiki/HTTP_402"}'
```

You'll get back `HTTP/1.1 402 Payment Required` with the x402 challenge in the response body.

---

## Links

- **Skim website** — <https://skim402.com>
- **Wallet setup guide** — <https://skim402.com/wallet>
- **API docs** — <https://skim402.com/docs>
- **x402 protocol** — <https://x402.org>
- **GitHub** — <https://github.com/JessieJanie/langchain-skim>

---

## License

MIT
