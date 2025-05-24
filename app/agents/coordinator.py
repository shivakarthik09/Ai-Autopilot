class CoordinatorAgent(BaseAgent):
    def __init__(self):
        super().__init__("CoordinatorAgent")
        self.client = OpenAIProjectClient(OPENAI_API_KEY)
        self.diagnostic_agent = DiagnosticAgent()
        self.automation_agent = AutomationAgent()
        self.writer_agent = WriterAgent()
        logging.info("Initialized CoordinatorAgent with all sub-agents")
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task with appropriate agents."""
        logging.info(f"CoordinatorAgent.execute called with task: {json.dumps(task, indent=2)}")
        try:
            # Validate input
            self.validate_input(task)
            logging.info("CoordinatorAgent input validation successful")
            
            # Determine required agents
            required_agents = await self._determine_agents(task["task"])
            logging.info(f"CoordinatorAgent determined required agents: {json.dumps(required_agents, indent=2)}")
            
            # Execute agents
            results = {}
            for agent_name in required_agents:
                logging.info(f"CoordinatorAgent executing agent: {agent_name}")
                agent_result = await self._execute_agent(agent_name, task)
                logging.info(f"CoordinatorAgent received result from {agent_name}: {json.dumps(agent_result, indent=2)}")
                results[agent_name] = agent_result
            
            # Combine results
            final_result = {
                "status": "success",
                "results": results
            }
            logging.info(f"CoordinatorAgent returning final result: {json.dumps(final_result, indent=2)}")
            return final_result
            
        except Exception as e:
            error_result = {
                "error": str(e),
                "status": "failed"
            }
            logging.error(f"CoordinatorAgent error: {str(e)}", exc_info=True)
            logging.error(f"CoordinatorAgent returning error result: {json.dumps(error_result, indent=2)}")
            return error_result
    
    async def _determine_agents(self, task: str) -> List[str]:
        """Determine which agents are needed for the task."""
        logging.info(f"CoordinatorAgent._determine_agents called with task: {task}")
        messages = [
            {"role": "system", "content": (
                "You are an expert at determining which specialized agents are needed for IT tasks. "
                "Available agents: diagnostic, automation, writer. "
                "Respond ONLY with a valid JSON object: {\"agents\": [\"diagnostic\", \"automation\", \"writer\"]}. "
                "Use only these lowercase names, no suffixes or extra text."
            )},
            {"role": "user", "content": f"Determine which agents are needed for this task:\n{task}"}
        ]
        
        try:
            logging.info(f"CoordinatorAgent sending request to OpenAI API with messages: {json.dumps(messages, indent=2)}")
            response = await self.client.create_chat_completion(
                messages=messages,
                model="gpt-3.5-turbo",
                temperature=0.7
            )
            
            # Log the raw response
            logging.info(f"CoordinatorAgent received response from OpenAI API: {json.dumps(response, indent=2)}")
            
            # Extract and parse the response
            content = response["choices"][0]["message"]["content"]
            logging.info(f"CoordinatorAgent extracted content from response: {content}")
            
            result = json.loads(content)
            # Normalize agent names to lowercase and strip 'agent' suffix if present
            agents = [a.lower().replace("agent", "").strip() for a in result["agents"]]
            logging.info(f"CoordinatorAgent parsed required agents: {json.dumps(agents, indent=2)}")
            return agents
            
        except Exception as e:
            logging.error(f"CoordinatorAgent error determining agents: {str(e)}", exc_info=True)
            raise
    
    async def _execute_agent(self, agent_name: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific agent."""
        logging.info(f"CoordinatorAgent._execute_agent called with agent_name: {agent_name}")
        agent_map = {
            "diagnostic": self.diagnostic_agent,
            "automation": self.automation_agent,
            "writer": self.writer_agent
        }
        
        if agent_name not in agent_map:
            error_msg = f"Unknown agent: {agent_name}"
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        agent = agent_map[agent_name]
        logging.info(f"CoordinatorAgent executing {agent_name} agent")
        return await agent.execute(task) 