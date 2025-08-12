# Run Multi-Agents

Execute multiple specialized agents in parallel for efficient task completion.

## Instructions

When handling complex tasks or fixing issue that can benefit from parallel processing:
1. Identify the available agents in .claude/agents directory
2. Analyze which agents are best suited for different aspects of the task. If it's convienent and when to launch multiple agents in parallele
3. Launch multiple specialized agents in parallel:
   - Use Task tool to spawn agents concurrently 
   - Coordinate agents for different parts of the same task
   - Leverage agent specializations (frontend, backend, testing, etc.)
4. Ensure agents work efficiently together without conflicts
5. Synthesize results from multiple agents into a cohesive solution

This approach maximizes performance and leverages specialized agent capabilities.