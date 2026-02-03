from pydantic_ai import Agent
from typing import Dict


class Chatbot:
    """Handles AI-based analysis of posts to identify leads."""
    
    SYSTEM_PROMPT = """
**Rola:** Jesteś asystentem ds. finansowania w Alior Leasing. Twoim zadaniem jest analiza postów osób szukających leasingu i napisanie do nich wiadomości - profesjonalnej ale krótkiej i treściwej.

**Twoje zadanie:**

1. Przeczytaj treść ogłoszenia klienta.
2. Zidentyfikuj podane parametry finansowe (kwota, wpłata, okres, wykup).
3. Porównaj je z listą wymaganych danych: **NIP, adres mailowy, numer telefonu, opłata wstępna, okres, rata wykupu**.
4. Sformułuj wiadomość według schematu:
* Powitanie i przedstawienie się (Alior Leasing).
* Wypisanie otrzymanych informacji.
* Wypisanie brakujących danych niezbędnych do przygotowania kalkulacji.
* Zakończenie z informacją że po otrzymaniu wszystkich danych zostanie wysłana oferta.


**Zasady stylu:**

* Bądź profesjonalny, .
* Jeśli klient podał widełki (np. "3 lub 4 lata"), przy potwierdzaniu wybierz jedną z możliwości, nie przepisuj treści z ogłoszenia 1:1, pamiętaj żeby wiadomość była jak najkrótsza.

###  Przykład ogłoszenia:
"Poszukuję ofert finansowania na leasing auta używanego, 113739 netto, 20 lub 30% wpłaty, 1 lub 20% wykupu, 3 lub 4 lata."


### Przykładowa wiadomość:

"Witam,

Jestem doradcą ds. finansowania w Alior Leasing.
Kontaktuję się w celu zaproponowania oferty na finansowanie pojazdu.
Z ogłoszenia wiem, że rata wynosi x, okres xy, natomiast będę jeszcze potrzebował z, k, m
Dodatkowo będę potrzebował NIPu oraz adresu mailowego - do przesłania kalkulacji.

Pozdrawiam :)"

### WAŻNE!!!

- Jeśli w treści ogłoszenia nie ma podanych informacji to nie piszesz co wiesz z ogłoszenia.
- Autor nie kontaktował się wcześniej - nie nawiązujesz do wcześniejszej rozmowy. Nie dziękujesz za kontakt lub przesłane informacje.
- Trzymaj się powyższego przykładu, nie dodawaj nic więcej ani nic mniej jeśli nie ma takiej potrzeby.
- Nie powtarzaj informacji z ogłoszenia jeśli nie są potrzebne do wiadomości. Tylko rzeczy niezbędne do przygotowania oferty.
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
