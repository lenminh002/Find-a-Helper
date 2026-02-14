"""
AI Helper module — wraps the OpenAI API and builds context from the database.
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


def get_available_tasks_summary():
    """Summarize the types of tasks available on the platform."""
    return (
        "Available task types on the platform include: "
        "Moving help, Grocery Runs, Dog Walking, Furniture Assembly, "
        "Yard Work, Tech Support, Cat Sitting, Car Wash, Tutoring, Heavy Lifting. "
        "Rewards typically range from $15 to $50."
    )


SYSTEM_PROMPT = """You are the AI assistant for "Find a Helper" — a community task marketplace where people post tasks they need help with, and helpers accept them.

Your role:
- Help users find relevant tasks
- Answer questions about the platform
- Give advice on pricing, task descriptions, and being a good helper/requester
- Be friendly, concise, and helpful

You have access to the user's profile and their current tasks. Use this context to give personalized answers.

Keep responses SHORT (2-3 sentences max) unless the user asks for detail."""


def build_messages(user_message, user_id, conversation_history=None):
    """Build the messages array for the OpenAI API."""
    context = (
        f"{get_user_context(user_id)}\n\n"
        f"{get_tasks_context()}\n\n"
        f"{get_available_tasks_summary()}"
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
    """Send a message to the LLM and get a response."""
    try:
        from openai import OpenAI

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return "⚠️ OpenAI API key not configured. Add OPENAI_API_KEY to your .env file."

        client = OpenAI(api_key=api_key)
        messages = build_messages(user_message, user_id, conversation_history)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=300,
            temperature=0.7
        )

        return response.choices[0].message.content

    except ImportError:
        return "⚠️ OpenAI package not installed. Run: pip install openai"
    except Exception as e:
        return f"⚠️ AI error: {str(e)}"
