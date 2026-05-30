import json
from pathlib import Path
from app.core.agent import ResearchAgent

questions = json.loads(Path('app/evals/eval_questions.json').read_text())
agent = ResearchAgent()

for item in questions:
    result = agent.ask(item['question'])
    text = result.answer.lower()
    hits = sum(term.lower() in text for term in item['expected_terms'])
    print('\nQUESTION:', item['question'])
    print('TERM COVERAGE:', f"{hits}/{len(item['expected_terms'])}")
    print('CONFIDENCE:', result.confidence)
    print(result.answer[:900])
