from __future__ import annotations

from collections import ChainMap, defaultdict, deque
from dataclasses import asdict, dataclass

from hibiscus.server.serve import HibiscusServer




@dataclass(init=False)
class Hibiscus:
    def __init__(
        self,
        agent: Optional[Union[agnoAgent, smolAgent, crewaiAgent]] = None,
        deploy_cloud: bool = False,
        debug_mode: bool = False,
        monitoring: bool = False,
        telemetry: bool = True,
    ):
        self.agent = agent
        self.deploy_cloud = deploy_cloud
        self.debug_mode = debug_mode
        self.monitoring = monitoring
        self.telemetry = telemetry

        if not self.agent:
            raise ValueError("We only support Agno, SmolAgents and CrewAI agents, More agents coming soon, look the documentation for more details")

        self.api_app = HibiscusServer(agent=self.agent)
        self.api_app.serve_app()


        


