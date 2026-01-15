from typing import List, Dict
from pydantic import BaseModel, Field
from pydantic_ai import Agent


class PostAnalysis(BaseModel):
    """Schema for post analysis results."""
    post_id: str = Field(description="Identyfikator analizowanego posta")
    is_lead: bool = Field(description="True jeśli autor szuka finansowania, False jeśli to reklama, cesja lub sprzedaż")
    reasoning: str = Field(description="Krótkie uzasadnienie decyzji")


class BatchAnalysisResult(BaseModel):
    """Schema for batch analysis results."""
    results: List[PostAnalysis]


class LeadAnalyzer:
    """Handles AI-based analysis of posts to identify leads."""
    
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
    
    def __init__(self, model: str = 'openai:gpt-4o-mini', batch_size: int = 5):
        """
        Initialize the lead analyzer.
        
        Args:
            model: AI model to use for analysis
            batch_size: Number of posts to analyze in each batch
        """
        self.batch_size = batch_size
        self.agent = Agent(
            model,
            system_prompt=self.SYSTEM_PROMPT,
            output_type=BatchAnalysisResult,
        )
    
    async def analyze_posts_batch(self, posts: List[Dict]) -> List[Dict]:
        """
        Analyze a batch of posts to identify leads.
        
        Args:
            posts: List of post dictionaries
            
        Returns:
            List of posts enriched with is_lead and reasoning fields
        """
        if not posts:
            return []
        
        posts_for_analysis = [{"id": p["id"], "content": p["content"]} for p in posts]
        input_text = f"Przeanalizuj poniższe posty:\n{str(posts_for_analysis)}"
        
        result = await self.agent.run(input_text)
        
        analysis_map = {analysis.post_id: analysis for analysis in result.output.results}
        
        enriched_posts = []
        for post in posts:
            analysis = analysis_map.get(post["id"])
            enriched_posts.append({
                **post,
                "is_lead": analysis.is_lead if analysis else False,
                "reasoning": analysis.reasoning if analysis else "No analysis"
            })
        
        return enriched_posts
    
    def batch_posts(self, posts: List[Dict]) -> List[List[Dict]]:
        """
        Split posts into batches for analysis.
        
        Args:
            posts: List of posts to batch
            
        Yields:
            Batches of posts
        """
        for i in range(0, len(posts), self.batch_size):
            yield posts[i:i + self.batch_size]

