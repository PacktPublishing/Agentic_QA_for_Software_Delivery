import anthropic
from dotenv import load_dotenv

load_dotenv()

story = open("product/stories/US-07-fast-delivery.md").read()

response = anthropic.Anthropic().messages.create(
    model="claude-sonnet-5-5",
    max_tokens=16000,
    system="You are a senior QA engineer. List the assumptions, risks (with a severity), questions and conflicts in this user story.",
    messages=[{"role": "user", "content": story}],
    output_config={"effort": "low"},
)

print("".join(block.text for block in response.content if block.type == "text"))