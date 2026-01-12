import os
from typing import List
from pydantic import BaseModel, Field
from pydantic_ai import Agent

# Ustaw swój klucz API (np. OpenAI, Anthropic)
# os.environ['OPENAI_API_KEY'] = 'sk-...'

# ---------------------------------------------------------
# 1. Definicja struktur danych (Schema)
# ---------------------------------------------------------

class PostAnalysis(BaseModel):
    post_id: str = Field(description="Identyfikator analizowanego posta")
    is_lead: bool = Field(description="True jeśli autor szuka finansowania, False jeśli to reklama, cesja lub sprzedaż")
    reasoning: str = Field(description="Krótkie uzasadnienie decyzji (np. 'Klient pyta o rabat', 'To jest oferta cesji')")

class BatchAnalysisResult(BaseModel):
    results: List[PostAnalysis]

# ---------------------------------------------------------
# 2. Definicja Agenta i System Promptu
# ---------------------------------------------------------

# Treść promptu systemowego z Twoimi zasadami
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
    'openai:gpt-4o-mini', # Zalecany model: tani i szybki, wystarczający do tego zadania
    result_type=BatchAnalysisResult,
    system_prompt=SYSTEM_PROMPT
)

# ---------------------------------------------------------
# 3. Przykład użycia
# ---------------------------------------------------------

# Symulacja danych wejściowych (lista postów)
facebook_posts = [
    {"id": "p1", "content": "Cześć, szukam leasingu na nowe BMW X5, wpłata 20%."},
    {"id": "p2", "content": "Odstąpię cesję na Audi A6, niska rata, bez odstępnego pilne!"},
    {"id": "p3", "content": "Czy ktoś mi wyliczy ofertę na ciągnik siodłowy? Jaki rabat mogę dostać?"},
    {"id": "p4", "content": "Sprzedam opony zimowe, stan idealny."},
    {"id": "p5", "content": "Poszukuję pożyczki leasingowej na maszynę rolniczą."}
]

# Konwersja listy postów do stringa dla modelu (można to sformatować ładniej)
input_text = f"Przeanalizuj poniższe posty:\n{str(facebook_posts)}"

async def main():
    # Wywołanie agenta
    result = await agent.run(input_text)
    
    # Wyświetlenie wyników
    print(f"Przeanalizowano {len(result.data.results)} postów:\n")
    
    for analysis in result.data.results:
        status = "✅ LEAD" if analysis.is_lead else "❌ ODRZUCONY"
        print(f"[{status}] ID: {analysis.post_id}")
        print(f"Powód: {analysis.reasoning}")
        print("-" * 30)

# Uruchomienie (w środowisku wspierającym async, np. skrypt .py)
if __name__ == '__main__':
    import asyncio
    asyncio.run(main())