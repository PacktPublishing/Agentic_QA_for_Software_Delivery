import anthropic
from dotenv import load_dotenv
from pathlib import Path
import sys

load_dotenv()

STORIES_DIR = Path(__file__).parents[2] / "product" / "stories"
MAX_TURNS = 10

TOOLS = [
    {
        "name": "list_user_stories",
        "description": "List the ID and title of every BookNest user story.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "read_user_story",
        "description": "Read a BookNest user story and its acceptance criteria.",
        "input_schema": {
            "type": "object",
            "properties": {"story_id": {"type": "string", "description": "e.g. US-03"}},
            "required": ["story_id"],
        },
    },
    {
        "name": "search_user_stories",
        "description": "Find the lines, in all user stories, that contain every word of the "
        "query (case-insensitive). Use it to find stories about the same behaviour.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "e.g. free shipping"}},
            "required": ["query"],
        },
    },
]

def list_user_stories() -> str:
    paths = sorted(STORIES_DIR.glob("US-*.md"))
    return "\n".join(path.read_text().splitlines()[0].removeprefix("# ") for path in paths)


def read_user_story(story_id: str) -> str:
    for path in STORIES_DIR.glob("US-*.md"):
        if path.name.startswith(f"{story_id.upper()}-"):
            return path.read_text()
    return f"There is no user story {story_id}."


def search_user_stories(query: str) -> str:
    words = query.lower().split()
    if not words:
        return "Please provide at least one word to search."

    matches = []
    for path in sorted(STORIES_DIR.glob("US-*.md")):
        for line in path.read_text().splitlines():
            if all(word in line.lower() for word in words):
                matches.append(f"{path.stem[:5]}: {line.strip()}")

    return "\n".join(matches) or f"No story contains all the words of '{query}'."


def run_tool(name: str, tool_input: dict) -> str:
    if name == "list_user_stories":
        return list_user_stories()
    if name == "read_user_story":
        return read_user_story(**tool_input)
    if name == "search_user_stories":
        return search_user_stories(**tool_input)
    return f"Error: unknown tool {name}."

def run_agent(messages: list) -> str: # 1. Messages starts with the user's input
    client = anthropic.Anthropic()

    for turn in range(1, MAX_TURNS + 1): # 7. Stop when the turns run out
        response = client.messages.create( # 2. Call the model with the whole context
            model="claude-sonnet-5-5",
            max_tokens=16000,
            system="You are a senior QA engineer. List the assumptions, risks (with a severity), questions and conflicts in this user story.",
            messages=messages,
            tools=TOOLS,
            output_config={"effort": "low"},
        )

        messages.append({"role": "assistant", "content": response.content}) # 3. Store the message coming from the model as part of the context

        if response.stop_reason != "tool_use": # 4. No tool requested? We are done. Just show the final answer
            break

        tool_results = []
        for block in response.content: # 5. Run every tool the model asked for
            if block.type == "tool_use":
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": run_tool(block.name, block.input),
                    }
                )

        messages.append({"role": "user", "content": tool_results}) # 6. Store the return from the function to the model as part of the context
    else:
        raise RuntimeError(f"The agent did not finish within {MAX_TURNS} turns.")

    if response.stop_reason == "max_tokens":
        raise RuntimeError("The answer was cut off by max_tokens, so it is not final.")
    
    return "".join(block.text for block in response.content if block.type == "text")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python agent.py <story_id>  (e.g. US-03)")

    story_id = sys.argv[1].upper()
    messages = [{"role": "user", "content": f"Review user story {story_id}."}]

    print(run_agent(messages))