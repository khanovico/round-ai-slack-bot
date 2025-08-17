from pydantic import BaseModel
from typing import Optional, List, Dict, Union, Literal
from app.ai import NL2SQLAgent, ChatHistoryManager
from app.ai.intent_classifier import IntentClassifierFactory, Intent
from app.core.logging_config import get_logger
from app.core.config import settings
from app.cache import get_cache
from app.observability import trace_async_method, trace_agent_call
from app.utils import create_and_upload_csv

class NL2SQLServiceResponse(BaseModel):
    question: str
    answer: str
    session_id: Optional[str] = None
    success: bool
    data: Union[str, List[Dict]]
    type: Literal["text", "table", "sql", "download"]

class NL2SQLService:
    def __init__(self):
        self.logger = get_logger("app.ai.services.nl2sql")
        # history manager
        self.chat_history_manager = ChatHistoryManager(max_cnt=settings.MAX_CHAT_HISTORY_CNT)

        # nl2sql agent
        self.nl2sql_agent = NL2SQLAgent(self.chat_history_manager)

        # intent classifiers
        self.regex_classifier = IntentClassifierFactory.get_regex_classifier(confidence_threshold=0.8)
        self.semantic_classifier = IntentClassifierFactory.get_semantic_classifier(confidence_threshold=0.6, 
                                                                                  fallback_intent=Intent.SQL_QUERY)
        
    def get_sql_key(self, session_id: str) -> str:
        return f"res:{session_id}:sql"
    
    def get_exec_res_key(self, session_id: str) -> str:
        return f"res:{session_id}:exec_res"
    
    async def get_last_sql(self, session_id: str) -> str:
        cache = await get_cache()
        return await cache.get(self.get_sql_key(session_id))
    
    async def get_last_exec_res(self, session_id: str) -> List[Dict]:
        cache = await get_cache()
        return await cache.get(self.get_exec_res_key(session_id))

    async def store_exec_result(self, session_id: str, sql: str, res: List[Dict]):
        cache = await get_cache()
        await cache.set(self.get_sql_key(session_id), sql)
        await cache.set(self.get_exec_res_key(session_id), res)

    @trace_async_method("nl2sql_service_run", capture_args=True, capture_result=True)
    async def run(self, question: str, session_id: str) -> NL2SQLServiceResponse:
        # Create session_id if session is not existing
        if not session_id:
            session_id = await self.chat_history_manager.create_session()
            self.logger.info(f"Created new session: {session_id}")

        res = NL2SQLServiceResponse(
            question=question,
            session_id=session_id,
            answer="",
            success=False,
            data="",
            type="text"
        )        

        # Intent classification with tracing
        with trace_agent_call("intent_classification", {"question": question, "session_id": session_id}) as trace_outputs:
            regex_result = self.regex_classifier.classify(question)
            if self.regex_classifier.is_confident(regex_result):
                intent = regex_result.intent
                trace_outputs.update({
                    "method": "regex",
                    "intent": intent.value,
                    "confidence": regex_result.confidence,
                    "metadata": regex_result.metadata
                })
                self.logger.info(f"Classified intent by Regex: {intent} with score {regex_result.confidence}")
            else:
                # Fallback to semantic
                semantic_result = self.semantic_classifier.classify(question)
                intent = semantic_result.intent
                trace_outputs.update({
                    "method": "semantic_fallback",
                    "intent": intent.value,
                    "confidence": semantic_result.confidence,
                    "metadata": semantic_result.metadata,
                    "regex_confidence": regex_result.confidence
                })
                self.logger.info(f"Classified intent by semantic: {intent} with score {semantic_result.confidence}")
        
        self.logger.info(f"Classified intent: {intent}")

        # Trigger logics according to intent
        if intent == Intent.GREETING:
            res.answer = "Hello, how can I help you?"
            res.success = True

        elif intent == Intent.SQL_QUERY:
            agent_res = await self.nl2sql_agent.ask(question, session_id)
            if agent_res["success"]:
                await self.store_exec_result(session_id, agent_res["metadata"]["sql_query"], 
                                       agent_res["metadata"]["exec_result"])
                self.logger.info(f"Successfully processed question: {question}")
                res.data=agent_res["structured_response"]["exec_result"]
                res.success = True
                if len(res.data) > 1:
                    res.type="table"
                else:
                    res.type="text"
            else:
                self.logger.warning(f"Failed to process question: {question} - {agent_res['answer']}")
            
            res.answer = agent_res["structured_response"]["interpreted_answer"]
        
        elif intent == Intent.SHOW_SQL:
            sql = await self.get_last_sql(session_id)
            if sql:
                res.success = True
                res.data=sql
                res.type="sql"
                res.answer="Here is the SQL Query I used to get the data:\n"
            else:
                res.answer = "No SQL query was excuted for your previous request."
        
        elif intent == Intent.EXPORT_CSV:
            exec_res = await self.get_last_exec_res(session_id)
            if exec_res:
                ( _, download_url) = create_and_upload_csv(exec_res)
                res.data = download_url
                res.success = True
                res.type="download"
                res.answer="Here is the download link of csv file showing the result:\n"

            else:
                res.answer = "No SQL query was excuted for your previous request."
        
        return res
