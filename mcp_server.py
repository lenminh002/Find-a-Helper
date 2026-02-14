"""
MCP Server for Find a Helper — exposes the app's database via MCP protocol.

Run standalone:  python mcp_server.py
"""

import sqlite3
import json
import sys

DATABASE = 'database.db'


def query_db(query, args=()):
    """Query the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(query, args)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def query_db_one(query, args=()):
    """Query a single row."""
    rows = query_db(query, args)
    return rows[0] if rows else None


# ============================================================
# MCP Server Setup
# ============================================================

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types

    server = Server("find-a-helper")

    # --- Resources ---

    @server.list_resources()
    async def list_resources():
        return [
            types.Resource(
                uri="helper://tasks/accepted",
                name="Accepted Tasks",
                description="All tasks the user has accepted",
                mimeType="application/json"
            ),
            types.Resource(
                uri="helper://users/current",
                name="Current User",
                description="The current user's profile",
                mimeType="application/json"
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str):
        if uri == "helper://tasks/accepted":
            tasks = query_db('SELECT id, title, description, reward, status FROM tasks ORDER BY id DESC')
            return json.dumps(tasks, indent=2)

        elif uri == "helper://users/current":
            user = query_db_one('SELECT id, username, bio, role, expertise, joined_date FROM users LIMIT 1')
            return json.dumps(user, indent=2) if user else "{}"

        raise ValueError(f"Unknown resource: {uri}")

    # --- Tools ---

    @server.list_tools()
    async def list_tools():
        return [
            types.Tool(
                name="search_tasks",
                description="Search accepted tasks by keyword. Returns matching tasks.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "Keyword to search in task titles and descriptions"
                        }
                    },
                    "required": ["keyword"]
                }
            ),
            types.Tool(
                name="get_task_stats",
                description="Get statistics about tasks: total count, average reward, status breakdown.",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            types.Tool(
                name="suggest_price",
                description="Suggest a fair price for a given task type.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_type": {
                            "type": "string",
                            "description": "The type of task, e.g. 'moving', 'tutoring', 'dog walking'"
                        }
                    },
                    "required": ["task_type"]
                }
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "search_tasks":
            keyword = arguments.get("keyword", "")
            tasks = query_db(
                "SELECT id, title, description, reward, status FROM tasks WHERE title LIKE ? OR description LIKE ?",
                (f"%{keyword}%", f"%{keyword}%")
            )
            return [types.TextContent(type="text", text=json.dumps(tasks, indent=2))]

        elif name == "get_task_stats":
            total = query_db_one("SELECT COUNT(*) as count, AVG(reward) as avg_reward FROM tasks")
            statuses = query_db("SELECT status, COUNT(*) as count FROM tasks GROUP BY status")
            result = {
                "total_tasks": total["count"] if total else 0,
                "average_reward": round(total["avg_reward"], 2) if total and total["avg_reward"] else 0,
                "by_status": {s["status"]: s["count"] for s in statuses}
            }
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "suggest_price":
            task_type = arguments.get("task_type", "").lower()
            # Simple price lookup based on common task types
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
                    return [types.TextContent(type="text", text=json.dumps(
                        {"task_type": task_type, **prices, "note": f"Based on platform averages for {key} tasks"},
                        indent=2
                    ))]
            return [types.TextContent(type="text", text=json.dumps(
                {"task_type": task_type, "min": 15, "max": 50, "typical": 30,
                 "note": "General estimate — price varies by complexity and location"},
                indent=2
            ))]

        raise ValueError(f"Unknown tool: {name}")

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream)

    if __name__ == "__main__":
        import asyncio
        print("Starting Find a Helper MCP Server...", file=sys.stderr)
        asyncio.run(main())

except ImportError:
    # MCP not installed — provide a fallback
    if __name__ == "__main__":
        print("MCP package not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)
