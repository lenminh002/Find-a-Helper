"""
AI Helper module — wraps the OpenAI API with function calling for task search.
"""

import os
import sqlite3
import json

DATABASE = 'database.db'


def _query_db(query, args=(), one=False):
    """Standalone DB query helper (no Flask context needed)."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(query, args)
    rows = cur.fetchall()
    conn.close()
    if one:
        return dict(rows[0]) if rows else None
    return [dict(r) for r in rows]


def get_user_context(user_id):
    """Get the current user's profile as context."""
    user = _query_db('SELECT username, bio, role, expertise, joined_date FROM users WHERE id = ?', (user_id,), one=True)
    if not user:
        return "No user profile found."
    return (
        f"Current user: {user['username']}\n"
        f"Role: {user['role']}\n"
        f"Bio: {user['bio'] or 'N/A'}\n"
        f"Expertise: {user['expertise'] or 'N/A'}\n"
        f"Joined: {user['joined_date']}"
    )


def get_tasks_context():
    """Get accepted tasks as context."""
    tasks = _query_db('SELECT title, description, reward, status FROM tasks ORDER BY id DESC LIMIT 10')
    if not tasks:
        return "No accepted tasks yet."
    lines = []
    for t in tasks:
        lines.append(f"- {t['title']} (${t['reward']}) — {t['description']}")
    return "Accepted tasks:\n" + "\n".join(lines)


def get_available_tasks_context():
    """Get currently available tasks from the map."""
    tasks = _query_db('SELECT map_id, title, description, reward FROM available_tasks ORDER BY map_id')
    if not tasks:
        return "No available tasks on the map right now."
    lines = []
    for t in tasks:
        lines.append(f"- [ID:{t['map_id']}] {t['title']} (${t['reward']}) — {t['description']}")
    return f"Available tasks on the map ({len(tasks)} total):\n" + "\n".join(lines)


# --- OpenAI Function Calling Tools ---

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_available_tasks",
            "description": "Search for available tasks on the map by keyword. Returns matching tasks with their IDs, titles, descriptions, and rewards.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Keyword to search for in task titles and descriptions (e.g. 'yard', 'moving', 'dog')"
                    }
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_all_tasks",
            "description": "List all currently available tasks on the map. Use this when the user asks what tasks are available, or wants to see all options.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "highlight_task",
            "description": "Highlight a specific task on the map by opening its popup. Use this after finding a relevant task to show it to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "The map ID of the task to highlight"
                    }
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_price",
            "description": "Suggest a fair price range for a given task type.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "description": "The type of task, e.g. 'moving', 'tutoring', 'dog walking'"
                    }
                },
                "required": ["task_type"]
            }
        }
    }
]


def execute_tool(name, arguments):
    """Execute a tool call and return the result."""
    if name == "search_available_tasks":
        keyword = arguments.get("keyword", "")
        tasks = _query_db(
            "SELECT map_id, title, description, reward FROM available_tasks WHERE title LIKE ? OR description LIKE ?",
            (f"%{keyword}%", f"%{keyword}%")
        )
        if not tasks:
            return json.dumps({"results": [], "message": f"No tasks found matching '{keyword}'"})
        return json.dumps({"results": tasks, "message": f"Found {len(tasks)} task(s) matching '{keyword}'"})

    elif name == "list_all_tasks":
        tasks = _query_db("SELECT map_id, title, description, reward FROM available_tasks ORDER BY map_id")
        if not tasks:
            return json.dumps({"results": [], "message": "No tasks currently available on the map."})
        return json.dumps({"results": tasks, "message": f"{len(tasks)} task(s) currently available"})

    elif name == "highlight_task":
        task_id = arguments.get("task_id")
        task = _query_db("SELECT map_id, title, reward FROM available_tasks WHERE map_id = ?", (task_id,), one=True)
        if task:
            return json.dumps({"highlighted": True, "task": task})
        return json.dumps({"highlighted": False, "message": "Task not found on map"})



    elif name == "suggest_price":
        task_type = arguments.get("task_type", "").lower()
        # Simple price lookup based on common task types (ported from mcp_server.py)
        price_guide = {
            "moving": {"min": 30, "max": 60, "typical": 50},
            "grocery": {"min": 15, "max": 30, "typical": 25},
            "dog walking": {"min": 15, "max": 25, "typical": 20},
            "furniture": {"min": 30, "max": 50, "typical": 40},
            "yard work": {"min": 25, "max": 45, "typical": 35},
            "tech support": {"min": 20, "max": 40, "typical": 30},
            "cat sitting": {"min": 30, "max": 50, "typical": 45},
            "car wash": {"min": 15, "max": 30, "typical": 20},
            "tutoring": {"min": 25, "max": 50, "typical": 40},
            "heavy lifting": {"min": 10, "max": 25, "typical": 15},
        }
        for key, prices in price_guide.items():
            if key in task_type:
                return json.dumps(
                    {"task_type": task_type, **prices, "note": f"Based on platform averages for {key} tasks"},
                    indent=2
                )
        return json.dumps(
            {"task_type": task_type, "min": 15, "max": 50, "typical": 30,
             "note": "General estimate — price varies by complexity and location"},
            indent=2
        )

    return json.dumps({"error": f"Unknown tool: {name}"})


SYSTEM_PROMPT = """You are the AI assistant for "Find a Helper" — a community task marketplace where people post tasks they need help with, and helpers accept them.

Your role:
- Help users find relevant tasks on the map
- Answer questions about the platform
- Give advice on pricing, task descriptions, and being a good helper/requester
- Be friendly, concise, and helpful

IMPORTANT — Tool usage rules:
- When a user asks about available tasks, mentions wanting to find work, or asks "what tasks are there?", ALWAYS use your tools.
- Use search_available_tasks when they mention a specific type (e.g. "find me yard work", "dog walking tasks").
- Use list_all_tasks when they ask generally (e.g. "what tasks are available?", "show me tasks").
- After finding tasks, use highlight_task to show the best match on the map.
- The task results will be shown as interactive cards in the chat. Summarize what you found briefly.

You also have context about the user's profile and their accepted tasks.

Keep responses SHORT (2-3 sentences max) unless the user asks for detail."""


def build_messages(user_message, user_id, conversation_history=None):
    """Build the messages array for the OpenAI API."""
    context = (
        f"{get_user_context(user_id)}\n\n"
        f"{get_tasks_context()}\n\n"
        f"{get_available_tasks_context()}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n--- Context ---\n" + context}
    ]

    # Add conversation history if any
    if conversation_history:
        for msg in conversation_history[-6:]:  # Keep last 6 messages for context
            messages.append(msg)

    messages.append({"role": "user", "content": user_message})
    return messages


def chat(user_message, user_id, conversation_history=None):
    """Send a message to the LLM with function calling and get a response."""
    try:
        from openai import OpenAI

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return {"reply": "⚠️ OpenAI API key not configured. Add OPENAI_API_KEY to your .env file."}

        client = OpenAI(api_key=api_key)
        messages = build_messages(user_message, user_id, conversation_history)

        highlight_task_id = None
        found_tasks = []

        # First call — may return tool calls
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            max_tokens=300,
            temperature=0.7
        )

        choice = response.choices[0]

        # Handle tool calls if any
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            # Add assistant's tool call message
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                result = execute_tool(fn_name, fn_args)

                # Track found tasks from search
                if fn_name in ("search_available_tasks", "list_all_tasks"):
                    parsed = json.loads(result)
                    if parsed.get("results"):
                        found_tasks = parsed["results"]

                # Track highlighted task
                if fn_name == "highlight_task":
                    parsed = json.loads(result)
                    if parsed.get("highlighted"):
                        highlight_task_id = fn_args.get("task_id")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

            # Second call — get final response after tool execution
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            choice = response.choices[0]

        reply = choice.message.content or "I found the task for you on the map!"

        return {"reply": reply, "highlight_task_id": highlight_task_id, "found_tasks": found_tasks}

    except ImportError:
        return {"reply": "⚠️ OpenAI package not installed. Run: pip install openai"}
    except Exception as e:
        return {"reply": f"⚠️ AI error: {str(e)}"}
