from crewai.agent import Agent




# Add tools to agent
researcher = Agent(
    role="AI Technology Researcher",
    goal="Research the latest AI developments",
    verbose=True
)

researcher.run("What is the latest AI development?")