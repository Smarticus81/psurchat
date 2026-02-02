"""
Base Agent Class with MCP Client Integration
All 17 agents inherit from this base class
Implements SOTA AI with automatic fallback to OpenAI/Anthropic
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
from abc import ABC, abstractmethod

from backend.config import AgentConfig, settings, get_fallback_provider
from backend.database.session import get_db_context
from backend.database.models import ChatMessage

# Optional AI imports with graceful fallback
try:
    from openai import AsyncOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from anthropic import AsyncAnthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import google.generativeai as genai
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False


class BaseAgent(ABC):
    """
    Base class for all PSUR agents
    Provides AI generation with automatic fallback and common functionality
    """
    
    def __init__(self, config: AgentConfig, session_id: int):
        self.config = config
        self.session_id = session_id
        self.name = config.name
        self.role = config.role
        
        # Get actual provider with fallback
        self.ai_provider, self.model = config.get_active_provider()
        
        # Initialize AI clients (all available ones for fallback)
        self.openai_client = None
        self.anthropic_client = None
        self.google_model = None
        self.xai_client = None  # Grok API client
        
        self._initialize_ai_clients()
        
        # Context and memory
        self.conversation_history: List[Dict[str, str]] = []
        self.context: Dict[str, Any] = {}
    
    def _initialize_ai_clients(self):
        """Initialize all available AI clients for fallback capability"""
        if HAS_OPENAI and settings.openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        if HAS_ANTHROPIC and settings.anthropic_api_key:
            self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        
        if HAS_GOOGLE and settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self.google_model = genai.GenerativeModel(settings.google_model_default)
        
        # xAI/Grok uses OpenAI-compatible API with different base URL
        if HAS_OPENAI and settings.xai_api_key:
            self.xai_client = AsyncOpenAI(
                api_key=settings.xai_api_key,
                base_url="https://api.x.ai/v1"
            )
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text using the assigned AI model with automatic fallback
        Falls back through: OpenAI -> xAI/Grok -> Google -> Anthropic
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
        
        Returns:
            Generated text
        """
        providers_to_try = [
            (self.ai_provider, self.model),
        ]
        
        # Add fallback chain - prioritize OpenAI and xAI due to Anthropic billing issues
        if self.ai_provider != "openai" and self.openai_client:
            providers_to_try.append(("openai", settings.openai_model_default))
        if self.ai_provider != "xai" and self.xai_client:
            providers_to_try.append(("xai", settings.xai_model_default))
        if self.ai_provider != "google" and self.google_model:
            providers_to_try.append(("google", settings.google_model_default))
        if self.ai_provider != "anthropic" and self.anthropic_client:
            providers_to_try.append(("anthropic", settings.anthropic_model_orchestrator))
        
        last_error = None
        for provider, model in providers_to_try:
            try:
                result = await self._generate_with_provider(provider, model, prompt, system_prompt)
                if result:
                    return result
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                # Check for billing/credit issues and skip to next provider
                if "credit" in error_msg or "billing" in error_msg or "balance" in error_msg:
                    print(f"Provider {provider} has billing issues, trying fallback...")
                else:
                    print(f"Provider {provider} failed: {e}, trying fallback...")
                continue
        
        raise RuntimeError(f"All AI providers failed. Last error: {last_error}")
    
    async def _generate_with_provider(
        self, 
        provider: str, 
        model: str, 
        prompt: str, 
        system_prompt: Optional[str]
    ) -> str:
        """Generate with specific provider"""
        
        if provider == "openai" and self.openai_client:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Use reasoning models for complex tasks
            if "o1" in model or "o3" in model:
                # Reasoning models use max_completion_tokens
                response = await self.openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_completion_tokens=self.config.max_tokens,
                )
            else:
                # Newer models (gpt-4.5+, gpt-5+) use max_completion_tokens
                # Older models (gpt-4, gpt-3.5) use max_tokens
                try:
                    response = await self.openai_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=self.config.temperature,
                        max_completion_tokens=self.config.max_tokens,
                    )
                except Exception as e:
                    if "max_completion_tokens" in str(e):
                        # Try with max_tokens for older models
                        response = await self.openai_client.chat.completions.create(
                            model=model,
                            messages=messages,
                            temperature=self.config.temperature,
                            max_tokens=self.config.max_tokens,
                        )
                    else:
                        raise
            return response.choices[0].message.content
        
        elif provider == "anthropic" and self.anthropic_client:
            system = system_prompt or f"You are {self.name}, a {self.role} agent."
            
            # Use extended thinking for complex reasoning
            if "opus" in model.lower() or "sonnet" in model.lower():
                response = await self.anthropic_client.messages.create(
                    model=model,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
            else:
                response = await self.anthropic_client.messages.create(
                    model=model,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
            return response.content[0].text
        
        elif provider == "google" and self.google_model:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = await self.google_model.generate_content_async(full_prompt)
            return response.text
        
        elif provider == "xai" and self.xai_client:
            # xAI/Grok uses OpenAI-compatible API
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await self.xai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return response.choices[0].message.content
        
        elif provider == "perplexity":
            # Fallback perplexity to OpenAI or xAI for generation
            # Perplexity is only used for search, not generation
            if self.openai_client:
                return await self._generate_with_provider(
                    "openai", 
                    settings.openai_model_default, 
                    prompt, 
                    system_prompt
                )
            elif self.xai_client:
                return await self._generate_with_provider(
                    "xai", 
                    settings.xai_model_default, 
                    prompt, 
                    system_prompt
                )
        
        return None
    
    async def post_message(
        self,
        message: str,
        to_agent: str = "all",
        message_type: str = "normal",
        metadata: Optional[Dict] = None
    ):
        """
        Post a message to the discussion forum
        
        Args:
            message: Message content
            to_agent: Target agent (default: "all" for broadcast)
            message_type: Message type (normal, system, error, warning, success)
            metadata: Optional metadata dict
        """
        with get_db_context() as db:
            chat_msg = ChatMessage(
                session_id=self.session_id,
                from_agent=self.name,
                to_agent=to_agent,
                message=message,
                message_type=message_type,
                message_metadata=metadata,
                timestamp=datetime.utcnow()
            )
            db.add(chat_msg)
            db.commit()
        
        # Also add to conversation history
        self.conversation_history.append({
            "from": self.name,
            "to": to_agent,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def request_peer_review(
        self, 
        content: str, 
        reviewer_agent: str,
        review_type: str = "content"
    ) -> Dict[str, Any]:
        """
        Request another agent to review content and get AI-generated feedback
        
        Args:
            content: Content to review
            reviewer_agent: Name of reviewing agent
            review_type: Type of review (content, data, calculation)
        
        Returns:
            Dict with review feedback and recommendations
        """
        # Post review request
        await self.post_message(
            f"@{reviewer_agent}, please review this {review_type}:\n\n{content[:500]}...",
            to_agent=reviewer_agent,
            message_type="normal",
            metadata={"review_type": review_type, "content_length": len(content)}
        )
        
        # Generate AI review feedback as the reviewer
        review_prompt = f"""As {reviewer_agent}, a peer reviewer in a PSUR generation system, 
review the following {review_type} submitted by {self.name}:

{content}

Provide:
1. Overall assessment (APPROVED, NEEDS_REVISION, or REJECTED)
2. Specific feedback points
3. Suggested improvements
4. Regulatory compliance check

Be thorough but constructive."""

        try:
            feedback = await self.generate(
                prompt=review_prompt,
                system_prompt=f"You are {reviewer_agent}, a quality assurance specialist reviewing PSUR content."
            )
            
            # Parse assessment from feedback
            assessment = "NEEDS_REVISION"
            if "APPROVED" in feedback.upper()[:100]:
                assessment = "APPROVED"
            elif "REJECTED" in feedback.upper()[:100]:
                assessment = "REJECTED"
            
            # Post the review response
            await self.post_message(
                f"Review from {reviewer_agent}:\n\n{feedback[:800]}...",
                to_agent=self.name,
                message_type="success" if assessment == "APPROVED" else "normal",
                metadata={"reviewer": reviewer_agent, "assessment": assessment}
            )
            
            return {
                "status": "completed",
                "reviewer": reviewer_agent,
                "assessment": assessment,
                "feedback": feedback,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "reviewer": reviewer_agent
            }
    
    async def check_user_interventions(self) -> List[Dict[str, Any]]:
        """
        Check for user intervention messages that need to be addressed
        
        Returns:
            List of user messages requiring attention
        """
        with get_db_context() as db:
            # Get recent user messages addressed to this agent or all
            user_messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == self.session_id,
                ChatMessage.from_agent == "User",
                ChatMessage.to_agent.in_(["all", self.name])
            ).order_by(ChatMessage.timestamp.desc()).limit(10).all()
            
            return [
                {
                    "id": msg.id,
                    "message": msg.message,
                    "timestamp": msg.timestamp.isoformat(),
                    "to_agent": msg.to_agent
                }
                for msg in user_messages
            ]
    
    async def respond_to_intervention(self, user_message: str) -> str:
        """
        Generate a response to user intervention
        
        Args:
            user_message: The user's intervention message
        
        Returns:
            Agent's response
        """
        response_prompt = f"""A user has intervened in the PSUR generation process with the following message:

"{user_message}"

As {self.name} ({self.role}), respond appropriately. If they're asking for changes, acknowledge and explain what you'll do. If they're asking questions, answer based on your expertise.

Keep your response professional and actionable."""

        response = await self.generate(
            prompt=response_prompt,
            system_prompt=self.get_personality_prompt()
        )
        
        await self.post_message(
            f"Responding to user intervention:\n\n{response}",
            to_agent="User",
            message_type="normal"
        )
        
        return response
    
    @abstractmethod
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's primary task
        Must be implemented by each agent
        
        Args:
            task: Task specification dict
        
        Returns:
            Task execution result
        """
        pass
    
    def get_personality_prompt(self) -> str:
        """
        Get the agent's personality system prompt
        Can be overridden by specific agents
        """
        return f"""You are {self.name}, a specialized {self.role} agent in a multi-agent PSUR (Periodic Safety Update Report) generation system.

Your expertise is in {self.role.lower()}.

You collaborate with 16 other AI agents through a public discussion forum. All your work is transparent and peer-reviewed.

Key behaviors:
- Be professional and precise
- Show your work and reasoning with specific data citations
- Request help from other agents when needed using @mentions
- Acknowledge corrections graciously
- Verify all data and calculations before including them
- Write in clear, regulatory-compliant language per MDR 2017/745
- Always cite your data sources
- Include quantitative metrics where applicable

You are generating content for a medical device regulatory document that will be reviewed by notified bodies. Accuracy and compliance are paramount."""
