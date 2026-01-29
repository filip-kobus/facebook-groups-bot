from typing import List, Dict
from pydantic import BaseModel, Field
from pydantic_ai import Agent


class PostAnalysis(BaseModel):
    """Schema for post analysis results."""
    post_id: str = Field(description="Identyfikator analizowanego posta")
    is_lead: bool = Field(description="True jeśli autor szuka finansowania, False jeśli to reklama, cesja lub sprzedaż")
    has_unseen_info: bool = Field(default=False, description="True jeśli istotne informacje są prawdopodobnie w załączniku którego nie ma w podanej treści posta")
    # reasoning: str = Field(description="Krótkie uzasadnienie decyzji")


class BatchAnalysisResult(BaseModel):
    """Schema for batch analysis results."""
    results: List[PostAnalysis]

class LeadAnalyzer:
    """Handles AI-based analysis of posts to identify leads."""
    
    SYSTEM_PROMPT = """
Jesteś ekspertem ds. analizy leadów leasingowych. Otrzymujesz listę postów z Facebooka. Dla każdego:

Oznacz jako is_lead=True tylko jeśli autor SZUKA finansowania/leasingu na firmę (np. "Szukam leasingu", "Poproszę o ofertę", "Ile wpłaty?", "Wyliczenie raty", "Potrzebuję finansowania"). Szukamy wartościowych leadów gdzie klient jest zdecydowany, ma firmę oraz nie posiada brudów w biku albo w bazie, chcemy tylko pewne leady.

Oznacz jako is_lead=False jeśli:
- Autor oferuje leasing/finansowanie (np. "Oferuję leasing", "Chętnie pomogę", "Jestem doradcą", "Finansowanie bez BIK"),
- Jeśli szuka auta i leasingu - szukam auta w najmie
- Jeśli szuka auta do kupna i później finansowania (np. "Kupię auto i wezmę leasing") - chcemy tylko finansowanie/leasing, bez szukania auta lub przedmiotu do leasingu (chyba że chodzi o BWM)
- Chce leasing na osobę prywatną, konsumencki ("Leasing dla osoby prywatnej", "Konsumencki"),
- Jeśli leasing jest jedną z opcji (szukam najmu lub leasingu)
- Szuka pracy/kierowców ("Szukam kierowcy", "Zatrudnię na taxi"),
- Wynajmuje auta ("Wynajmę auto pod taxi"),
- Chce sprzedać/odstąpić/przejąć leasing (cesja, "odstąpię", "przejmę leasing"),
- Jest dealerem/komisem ("Dostępny od ręki", "Zapraszamy do salonu"),
- Chce leasing na osobę prywatną,
- Chce leasing bez weryfikacji baz/BIK.

Przykłady:
- "Kto zrobi leasing?" -> TRUE
- "Zrobię leasing" -> FALSE
- "Szukam kierowców na auta firmowe" -> FALSE

---

**WAŻNE: has_unseen_info**
Jeśli w treści posta jest odniesienie do brakującego załącznika (np. "szczegóły na zdjęciu", "kalkulacja w załączniku"), ustaw has_unseen_info=True. W przeciwnym razie ustaw has_unseen_info=False. To pole jest opcjonalne i powinno być True tylko wtedy, gdy tekst sugeruje brakujące istotne informacje w załączniku.
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

