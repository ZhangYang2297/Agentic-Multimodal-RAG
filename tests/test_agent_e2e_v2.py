
import sys, os, time
sys.path.insert(0, '.')
from src.retrieval.engine import RetrievalEngine
from src.retrieval.config import RetrievalConfig
from src.agent.graph import build_agent
from src.agent.llm import LLMService

print('init engine...')
engine = RetrievalEngine(
    persist_dir='outputs/test_chroma_travel',
    registry_path='outputs/test_registry.json',
    bm25_db_path='outputs/test_bm25/bm25_index.db',
    config=RetrievalConfig,
    enable_reranker=True,
)

print('manual search...')
results = engine.search('成都有哪些必去的旅游景点？')
print(f'results: {len(results)}')

print('build agent...')
llm = LLMService(temperature=0.3)
agent = build_agent(engine, llm)

state = {
    'query': '成都有哪些必去的旅游景点？',
    'search_summary': 'pending',
    'evaluation': 'pending',
    'active_query': '',
    'retry_count': 0,
    'max_retries': 2,
    'search_results': None,
    'answer': None,
    'messages': [],
}

print('agent invoke...')
t0 = time.perf_counter()
result = agent.invoke(state)
elapsed = time.perf_counter() - t0
ans = result.get('answer', '') or ''
print(f'elapsed: {elapsed:.1f}s')
print(f'answer ({len(ans)} chars): {ans[:200]}')
engine.close()
