## About the app:
- Find a Helper is a web application that offers a platform for users to post tasks they need help with and for helpers to find tasks they can do with AI integrated to help them with their tasks.

## How to run program:
- Install dependencies: pip install -r requirements.txt
- Add .env file with OPENAI_API_KEY=your_openai_api_key
- Run python app.py on Windows or python3 app.py on Mac
- *Note*: Don't need to create database.db manually, it will be created automatically with init_db() in app.py

`dummy_tasks.py` has dummy tasks for testing purposes.

## AI functionality:

- talk
- search tasks
- get tasks statistic
- suggest price
- Smart Task Recommendation: 
    - The AI assistant can now provide personalized task recommendations based on your profile.
    - `get_recommended_tasks` tool uses AI to match your expertise and bio with available tasks.
    - **How to Use**:
        - Ensure your profile has some expertise listed (e.g., "Gardening", "Moving").
        - Ask the AI: "What tasks should I do?" or "Find me work".
    - It should return a ranked list with reasons why each task fits you.

- Conversational Task Creation
    - **How to Use**:
        - Example: "I need help moving a couch this Saturday"
        - AI will create a task with title, description, reward and will ask for more information if needed before posting.

- Smart match score between helper's expertise and task
    - High Match: Purple color
    - Medium Match: Orange color
    - Low Match: Red color

- MCP is available for outside AI agent to use our app's database
    
Future updates / Ideas:
- AI Profile Optimizer
- Safety & Content Moderation
- Multilingual Translation & Support



