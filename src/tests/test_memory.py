# Create agent and enable long term memory
agent = MyAgent()
agent.use_long_term_memory = True

# Initialize persistent memory
memory = LongTermMemory()
memory.recover_memory(agent.name)

# Set memory in agent context
context = AgentContext()
context.memory = memory
context.long_term_memory = memory
agent.context = context

# Agent observes environment
context.news = agent.observe()

# Agent thinks and decides action
context.todo = agent.think(context.news, context.memory)

# Agent acts
msg = agent.act(context.todo)::

# Reply is saved to long term memory
context.memory.add(msg)
