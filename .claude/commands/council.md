Run the Agent Council on a question and return the council's decision.

The council uses a Leader agent (Agent A) that routes the query to relevant specialists (Strategist, Critic, Researcher, Executor), gathers their independent perspectives, and delivers a final synthesised judgment.

Usage:
  /council <your question>
  /council --interactive
  /council --kb list
  /council --memory list

Instructions:
1. Run `bash $CLAUDE_PROJECT_DIR/council.sh $ARGUMENTS` from the council project directory.
2. If no ANTHROPIC_API_KEY is in the environment, remind the user to set it or create a .env file.
3. Show the full output including which agents were consulted and the final decision.
4. If the user asks a follow-up, run the command again with the new question — session context persists within the same shell session.

Arguments: $ARGUMENTS
