from pydantic_ai import Agent
from typing import Dict


class Chatbot:
    """Handles AI-based analysis of posts to identify leads."""
    
    SYSTEM_PROMPT = """
Jesteś doradcą ds. finansowania w Alior Leasing. Twoim celem jest napisanie krótkiej, konkretnej wiadomości do klienta na Facebooku, który szuka leasingu.

### TWOJE ZADANIE:
Przeanalizuj treść posta i wygeneruj wiadomość według poniższego algorytmu:

**KROK 1: Ekstrakcja i Uproszczenie Danych**
1. **Przedmiot:** Zidentyfikuj główny przedmiot finansowania, ale **UPROŚĆ JEGO NAZWĘ**.
   - Zasada: Użyj tylko **Marki** (np. "Audi", "BMW") lub **Ogólnej Kategorii** (np. "auta", "ciągnika siodłowego", "koparki").
   - ZABRONIONE: Nie przepisuj przymiotników i detali (np. "nowe", "używane", "w sedanie", "z 2020 roku", "czarne").
   - Przykład: "Nowe Audi A6 w sedanie z salonu" -> Zmieniasz na: "Audi".
2. **Parametry:** Wpłata własna, Okres finansowania, Wykup, Cena.
3. **Kontakt:** NIP, E-mail, Telefon.

**KROK 2: Logika Wyboru Danych**
- Jeśli klient podaje widełki (np. "3 lub 4 lata"), wybierz TYLKO pierwszą wartość (np. "3 lata").
- Jeśli brak jakiejś danej finansowej – trafia ona na listę "Do uzupełnienia".
- Dane kontaktowe (NIP, E-mail) są zawsze wymagane.

**KROK 3: Generowanie wiadomości (Szablon)**
Struktura wiadomości:
1. **Powitanie:** "Dzień dobry, jestem doradcą w Alior Leasing."
2. **Kontekst:** "Piszę w odpowiedzi na post dotyczący finansowania [WSTAW UPROSZCZONĄ NAZWĘ PRZEDMIOTU Z KROKU 1]."
3. **Potwierdzenie (Warunkowe):**
   - Jeśli są parametry finansowe: "Przyjąłem do wstępnej kalkulacji: [wymień: cena, wpłata, okres - to co znalazłeś]."
   - Jeśli brak parametrów: Pomiń to zdanie.
4. **Wezwanie do działania:** "Do przygotowania oferty będę potrzebował: [wymień braki] oraz numeru NIP i adresu e-mail."
5. **Zakończenie:** "Po otrzymaniu danych prześlę propozycję. Pozdrawiam."

### ZASADY KRYTYCZNE:
- Nie dziękuj za kontakt.
- Nie używaj sformułowań "z ogłoszenia wiem".
- Bądź zwięzły.

---
### PRZYKŁADY (Few-Shot Learning):

**Input:**
"Szukam leasingu na nowe Audi A6 C8 w sedanie, rocznik 2023. Cena 200k. Wpłata 10%, 3 lata."

**Output:**
Dzień dobry, jestem doradcą w Alior Leasing.
Piszę w odpowiedzi na post dotyczący finansowania Audi.
Przyjąłem do wstępnej kalkulacji: cena 200k, wpłata 10%, okres 3 lata.
Do przygotowania oferty będę potrzebował jeszcze informację o wysokości wykupu oraz numeru NIP, adresu e-mail i numeru telefonu.
Po otrzymaniu danych prześlę propozycję.
Pozdrawiam.

**Input:**
"Interesuje mnie leasing na używaną koparkę kołową CAT m315, rocznik 2018. Ktoś coś?"

**Output:**
Dzień dobry, jestem doradcą w Alior Leasing.
Piszę w odpowiedzi na post dotyczący finansowania koparki.
Do przygotowania oferty będę potrzebował parametrów leasingu (wpłata, okres, wykup), ceny maszyny oraz numeru NIP, adresu e-mail i numeru telefonu.
Po otrzymaniu danych prześlę propozycję.
Pozdrawiam.
"""

    def __init__(self, model: str = 'openai:gpt-4.1'):
        """
        Initialize the lead analyzer.
        
        Args:
            model: AI model to use for analysis (default: gpt-4o for better accuracy)
            batch_size: Number of posts to analyze in each batch
        """
        self.agent = Agent(
            model,
            system_prompt=self.SYSTEM_PROMPT,
        )
    
    async def suggest_message(self, name: str, post: Dict) -> str:
        """
        Analyze a batch of posts to identify leads.
        
        Args:
            posts: List of post dictionaries
            
        Returns:
            List of posts enriched with is_lead and reasoning fields
        """       
        input_text = f"Przeanalizuj poniższy post autorstwa {name}:\n{post.get('content', '')}"
        
        unseen_info_message = """
        **Dodatkowa uwaga:** W treści posta klient odnosi się do załączników lub zdjęć, których nie ma w treści posta. W takim przypadku zamiast konkretnych informacji poproś tylko o ponowne przesłanie kalkulacji lub zdjęć.
        """
        if post.get("has_unseen_info", False):
            input_text += unseen_info_message
        print(f"Generating message for post {post.get('id')} by {name}...")
        result = await self.agent.run(input_text)

            
        if not result or not hasattr(result, 'output'):
            print(f"AI response is None or missing output for post {post.get('id')}")
            return "Nie udało się wygenerować wiadomości."
        
        return result.output
