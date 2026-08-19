"""
mentor/ — AI Startup Mentor package
Sits on top of the CRAG blueprint pipeline.

Folder structure:
    mentor/
    ├── __init__.py
    ├── context.py            ← builds MentorContext from blueprint output
    ├── memory.py             ← MentorSession + conversation + tool cache
    ├── intent_classifier.py  ← Groq classifies question → 1 of 14 intents
    ├── tool_router.py        ← intent → tool calls mapping
    ├── synthesizer.py        ← Granite generates cited answer
    ├── mentor_agent.py       ← main orchestrator (ask)
    ├── mentor_db.py          ← SQLite persistence for mentor sessions
    └── tools/
        ├── __init__.py
        ├── blueprint_tool.py ← searches within MentorContext dict
        ├── tavily_tool.py    ← live web search via Tavily
        └── chromadb_tool.py  ← ChromaDB PDF retrieval
"""
