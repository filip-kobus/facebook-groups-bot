from typing import List, Dict
from pydantic import BaseModel, Field
from pydantic_ai import Agent


class PostAnalysis(BaseModel):
    """Schema for post analysis results."""
    post_id: str = Field(description="Identyfikator analizowanego posta")
    is_lead: bool = Field(description="True jeśli autor szuka finansowania, False jeśli to reklama, cesja lub sprzedaż")
    # reasoning: str = Field(description="Krótkie uzasadnienie decyzji")


class BatchAnalysisResult(BaseModel):
    """Schema for batch analysis results."""
    results: List[PostAnalysis]


class LeadAnalyzer:
    """Handles AI-based analysis of posts to identify leads."""
    
    SYSTEM_PROMPT = """
Jesteś ekspertem ds. analizy leadów leasingowych. Twoim zadaniem jest filtrowanie postów z Facebooka.
Otrzymasz listę postów. Dla każdego z nich musisz zdecydować, czy autor jest potencjalnym klientem szukającym finansowania (leasingu/pożyczki).

KLUCZOWE ZASADY (BARDZO WAŻNE):
Szukamy TYLKO osób, które CHCĄ KUPIĆ/WZIĄĆ leasing (NIE PRZEJĄĆ!!!). Eliminujemy sprzedawców i pośredników.

Oznacz jako TRUE (is_lead=True), tylko jeśli autor SZUKA finansowania:
- Pisze "Szukam leasingu", "Szukam oferty na...", "Poproszę o ofertę".
- Pyta o warunki ("Jaki procent", "Ile wpłaty", "Czy dostanę leasing").
- Prosi o wyliczenie raty.
- Szuka samochodu i pyta o możliwości finansowania.

Oznacz jako FALSE (is_lead=False) w każdym innym przypadku, SZCZEGÓLNIE GDY:
1. Autor OFERUJE leasing/finansowanie (np. "Chętnie pomogę", "Zapraszam do kontaktu", "Oferuję leasing", "Jestem doradcą", "Finansowanie bez BIK").
2. Autor OFERUJE pracę lub szuka kierowców (np. "Szukam kierowcy", "Zatrudnię na taxi", "Podepnę pod flotę").
3. Autor WYNAJMUJE auta (np. "Wynajmę auto pod taxi", "Auto do wynajęcia", "Wynajem krótko/długoterminowy").
4. Autor CHCE SPRZEDAĆ auto lub ODSTĄPIĆ leasing (cesja, "odstąpię", "sprzedam").
5. Autor CHCE PRZEJĄĆ leasing na inną firmę (cesja, "przejmę leasing", "wezmę od kogoś leasing").
6. Autor to dealer lub komis samochodowy reklamujący swoje auta ("Dostępny od ręki", "Zapraszamy do salonu").

PAMIĘTAJ:
- "Kto zrobi leasing?" -> TRUE (potencjalny klient)
- "Zrobię leasing" -> FALSE (konkurencja)
- "Szukam kierowców na auta firmowe" -> FALSE (rekrutacja/wynajem)
"""
    
    def __init__(self, model: str = 'openai:gpt-4.1', batch_size: int = 5):
        """
        Initialize the lead analyzer.
        
        Args:
            model: AI model to use for analysis (default: gpt-4o for better accuracy)
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
        
        posts_for_analysis = [{"id": p["id"], "content": p["content"][:300]} for p in posts]
        input_text = f"Przeanalizuj poniższe posty:\n{str(posts_for_analysis)}"
        
        result = await self.agent.run(input_text)
        
        analysis_map = {analysis.post_id: analysis for analysis in result.output.results}
        
        enriched_posts = []
        for post in posts:
            analysis = analysis_map.get(post["id"])
            enriched_posts.append({
                **post,
                "is_lead": analysis.is_lead if analysis else False,
                # "reasoning": analysis.reasoning if analysis else "No analysis"
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

