# ⚡ LUMINA — AI DevOps Troubleshooter

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-LangGraph-orange.svg" alt="LangGraph">
  <img src="https://img.shields.io/badge/LLM-Gemini_2.5_Flash-red.svg" alt="Gemini">
  <img src="https://img.shields.io/badge/Search-Tavily_AI-cyan.svg" alt="Tavily">
  <img src="https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg" alt="Streamlit">
</p>

> **Diagnose. Research. Fix. Verify — Autonomously.**

LUMINA is an **Agentic AI-powered troubleshooting system** designed to solve complex DevOps, Cloud, and Software Engineering errors. Unlike standard chatbots, LUMINA operates as a **Stateful Agent** that researches real-world documentation and performs a **Self-Reflection loop** to critique and refine its own solutions before presenting them to the user.

---

## 🌟 Key Features

- 🔍 **Intelligent Triage**: Automatically classifies errors (Syntax, Logic, Environment, Dependency, Permission) to determine the best fix strategy.
- 🌐 **Real-Time Grounding**: Integrated with **Tavily AI** to browse the 2026 web for the latest documentation, GitHub issues, and StackOverflow threads.
- 🔁 **Self-Reflection Loop**: Implements a "Reviewer Node" that acts as a Senior QA Engineer, sending solutions back for research if they are risky or incomplete.
- 🧠 **Stateful Memory**: Uses LangGraph to track refinement history, ensuring the agent learns from "REDO" signals and converges on a perfect fix.
- 🎯 **Developer-First UI**: A premium, high-contrast Streamlit interface focused on speed and "Progressive Disclosure" of technical details.

---

## 🧠 Architecture & Workflow

LUMINA utilizes a **Directed Acyclic Graph (DAG)** with feedback loops to manage the lifecycle of a bug fix:



### The Pipeline:
1. **Classifier**: Triages the raw error log.
2. **Researcher**: Conducts memory-aware web searches.
3. **Coder**: Synthesizes a comprehensive patch (Root Cause, Fix, Verification).
4. **Reviewer**: Critiques the patch for safety and side effects.
5. **Router**: If `CLEAN`, moves to output. If `REDO`, loops back to Research with "Lessons Learned."

---

## 🛠️ Tech Stack

- **Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph) (State Machine)
- **Brain**: Google Gemini 2.5 Flash
- **Search**: Tavily AI (Agent-specialized search)
- **Framework**: LangChain
- **Interface**: Streamlit
- **Language**: Python 3.10+

---

## 🧑‍💻 Developer
Swarangi Kothawade Computer Science & Engineering (AI & Data Science) LinkedIn | GitHub

⭐ Vision
Toward self-healing software systems—where AI doesn't just assist the developer, but autonomously maintains the health of the cloud infrastructure. 🚀
