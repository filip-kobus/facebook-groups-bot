from typing import List, Dict
from pydantic import BaseModel, Field
from pydantic_ai import Agent

class PostAnalysis(BaseModel):
    post_id: str = Field(description="Identyfikator analizowanego posta")
    is_lead: bool = Field(description="True jeśli autor szuka finansowania, False jeśli to reklama, cesja lub sprzedaż")
    reasoning: str = Field(description="Krótkie uzasadnienie decyzji")

class BatchAnalysisResult(BaseModel):
    results: List[PostAnalysis]

SYSTEM_PROMPT = """
Jesteś ekspertem ds. analizy leadów leasingowych. Twoim zadaniem jest filtrowanie postów z Facebooka.
Otrzymasz listę postów. Dla każdego z nich musisz zdecydować, czy autor jest potencjalnym klientem szukającym finansowania (leasingu/pożyczki).

ZASADY FILTROWANIA:

Oznacz jako TRUE (is_lead=True), jeśli post zawiera intencję uzyskania oferty lub finansowania, np.:
- Autor prosi o przygotowanie oferty lub kalkulacji ("przygotuję ofertę", "wykona kalkulację").
- Autor pyta o rabaty ("Jaki rabat", "Ile rabatu").
- Autor wprost pisze, że szuka ("Szukam leasingu", "Szukam oferty", "poszukuje pożyczki").
- Autor prosi o ocenę oferty ("Czy to jest dobra oferta", "lepszą ofertę").
- Autor pyta o warunki ("warunków leasingu", "w leasingu").

Oznacz jako FALSE (is_lead=False), jeśli post dotyczy rynku wtórnego, przejęć lub sprzedaży, np.:
- Słowa kluczowe związane z cesją: "cesja", "odstąpię", "przejmę", "do przejęcia", "bez odstępnego".
- Słowa kluczowe związane z najmem/braniem: "najem długotrwały", "wezmę", "przyjmę".
- Słowa kluczowe sprzedażowe: "na sprzedaż", "oddać".

UWAGA: Bądź precyzyjny. Jeśli ktoś pisze "Odstąpię leasing", to NIE jest Twój klient (szukasz osób, które chcą wziąć nowy leasing, a nie pozbyć się starego).
"""

agent = Agent(
    'openai:gpt-4o-mini',
    system_prompt=SYSTEM_PROMPT,
    output_type=BatchAnalysisResult,
)

async def analyze_posts_batch(posts: List[Dict]) -> List[Dict]:
    if not posts:
        return []
    
    posts_for_analysis = [{"id": p["id"], "content": p["content"]} for p in posts]
    input_text = f"Przeanalizuj poniższe posty:\n{str(posts_for_analysis)}"
    
    result = await agent.run(input_text)
    
    analysis_map = {analysis.post_id: analysis for analysis in result.data.results}
    
    enriched_posts = []
    for post in posts:
        analysis = analysis_map.get(post["id"])
        enriched_posts.append({
            **post,
            "is_lead": analysis.is_lead if analysis else False,
            "reasoning": analysis.reasoning if analysis else "No analysis"
        })
    
    return enriched_posts

def batch_posts(posts: List[Dict], batch_size: int = 5):
    for i in range(0, len(posts), batch_size):
        yield posts[i:i + batch_size]
