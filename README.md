How to run program:
- Install dependencies: pip install -r requirements.txt
- Add .env file with OPENAI_API_KEY=your_openai_api_key
- Run python app.py on Windows or python3 app.py on Mac
Note: Don't need to create database.db manually, it will be created automatically with init_db() in app.py

AI functionality:

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
    
Idea:
- AI Profile Optimizer
- Safety & Content Moderation
- Multilingual Translation & Support


