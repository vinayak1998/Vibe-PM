# AI PM Agent

An AI product-manager agent that turns product ideas into structured specs through a 3-phase conversational pipeline: **Discovery → Scoping → Spec Writer**. It runs a PM-style discovery interview, proposes a RICE-scoped MVP with comparable products, then writes a phased product spec you can hand to a developer or code-gen tool. Built with [Chainlit](https://chainlit.io/). See [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) for architecture.

## Why and by whom

This project exists to turn rough product ideas into clear, phased product specs with minimal manual PM process—one conversation instead of multiple back-and-forths. Created by **[Vinayak Rastogi](https://www.linkedin.com/in/vinayak1998/)**.

## Replicate locally

1. **Clone the repo**
   ```bash
   git clone https://github.com/vinayak1998/<REPO_NAME>.git
   cd <REPO_NAME>
   ```

2. **Python 3.9+** required.

3. **Create and activate a virtual env**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment**  
   Copy `.env.example` to `.env` and set your Groq API key (see [config.py](config.py)):
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```
   Get a key at [Groq Console](https://console.groq.com/).

6. **Run the app**
   ```bash
   chainlit run app.py
   ```

7. Open the URL shown in the terminal (e.g. http://localhost:8000).

## Project structure

| Path | Description |
|------|--------------|
| `app.py` | Chainlit entry point; session and message handling |
| `orchestrator.py` | Code orchestrator; phase routing and handoffs |
| `agents/` | Discovery, Scoping, Spec Writer agents |
| `models/` | Schemas and LLM routing |
| `prompts/` | System and extraction prompts |
| `tools/` | Extraction, completeness, intent, web search |
| `eval/` | Eval runner and scenarios |

**Requirements:** See [requirements.txt](requirements.txt).

## Bugs and contributions

- **Bugs:** Open an issue on GitHub.
- **PRs:** Welcome. Use branch names like `feature/short-name` or `fix/short-name`; keep PR titles descriptive; reference issues with `Fixes #N` where applicable.

## License

This project is open source and licensed under the **MIT License**. See [LICENSE](LICENSE).
