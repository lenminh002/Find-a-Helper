"""
MCP Server for Find a Helper — exposes the app's database via MCP protocol.

Run standalone:  python mcp_server.py
"""

import sqlite3
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()

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
            
            # Query database for similar tasks from both tables
            similar_tasks = query_db(
                "SELECT title, reward FROM tasks WHERE title LIKE ? OR description LIKE ?",
                (f"%{task_type}%", f"%{task_type}%")
            )
            available_tasks = query_db(
                "SELECT title, reward FROM available_tasks WHERE title LIKE ? OR description LIKE ?",
                (f"%{task_type}%", f"%{task_type}%")
            )
            
            # Combine results
            all_similar = similar_tasks + available_tasks
            
            if not all_similar:
                # Fallback: get all tasks if no exact matches
                all_similar = query_db("SELECT title, reward FROM tasks UNION SELECT title, reward FROM available_tasks")
            
            # Calculate statistics
            rewards = [task["reward"] for task in all_similar if task["reward"]]
            
            if rewards:
                price_min = round(min(rewards), 2)
                price_max = round(max(rewards), 2)
                price_avg = round(sum(rewards) / len(rewards), 2)
                
                # Use OpenAI to suggest a price with reasoning
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                    
                    prompt = f"""Based on the following task pricing data from our platform, suggest a fair price for a '{task_type}' task.

Database statistics:
- Minimum price seen: ${price_min}
- Maximum price seen: ${price_max}
- Average price: ${price_avg}
- Number of similar tasks: {len(rewards)}

Sample tasks:
{json.dumps(all_similar[:5], indent=2)}

Provide:
1. A suggested price (single number)
2. A recommended price range (min-max)
3. Brief reasoning (2-3 sentences)

Respond in JSON format:
{{
  "suggested_price": <number>,
  "price_range": {{"min": <number>, "max": <number>}},
  "reasoning": "<text>"
}}"""
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"}
                    )
                    
                    ai_result = json.loads(response.choices[0].message.content)
                    result = {
                        "task_type": task_type,
                        "suggested_price": ai_result.get("suggested_price", price_avg),
                        "price_range": ai_result.get("price_range", {"min": price_min, "max": price_max}),
                        "reasoning": ai_result.get("reasoning", "Based on platform data"),
                        "data_stats": {
                            "sample_size": len(rewards),
                            "db_min": price_min,
                            "db_max": price_max,
                            "db_avg": price_avg
                        }
                    }
                    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
                    
                except Exception as e:
                    # Fallback if OpenAI fails
                    result = {
                        "task_type": task_type,
                        "suggested_price": price_avg,
                        "price_range": {"min": price_min, "max": price_max},
                        "reasoning": f"Based on {len(rewards)} similar tasks in our database",
                        "error": str(e)
                    }
                    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            else:
                # No data available
                return [types.TextContent(type="text", text=json.dumps({
                    "task_type": task_type,
                    "suggested_price": 30,
                    "price_range": {"min": 15, "max": 50},
                    "reasoning": "No similar tasks found in database. Using general platform estimate."
                }, indent=2))]

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
