# Domyślne zadanie, wyświetla pomoc
help:
	@echo "Dostępne komendy:"
	@echo ""
	@echo "Ogólne:"
	@echo "  make setup         - Instaluje zależności projektu."
	@echo "  make admin         - Uruchamia panel administratora."
	@echo ""
	@echo "Operacje dla wszystkich botów:"
	@echo "  make scrape        - Scrapuje dla wszystkich enabled botów."
	@echo "  make classify      - Klasyfikuje posty dla wszystkich enabled botów."
	@echo "  make send-messages - Wysyła wiadomości dla wszystkich enabled botów."
	@echo ""
	@echo "Operacje dla konkretnego bota:"
	@echo "  make scrape-leasing        - Scrapuje tylko dla bota leasing."
	@echo "  make scrape-car-buyers     - Scrapuje tylko dla bota car_buyers."
	@echo "  make classify-leasing      - Klasyfikuje tylko dla bota leasing."
	@echo "  make classify-car-buyers   - Klasyfikuje tylko dla bota car_buyers."
	@echo "  make send-leasing          - Wysyła wiadomości tylko dla bota leasing."
	@echo "  make send-car-buyers       - Wysyła wiadomości tylko dla bota car_buyers."
	@echo ""
	@echo "Narzędzia:"
	@echo "  make list          - Wyświetla listę leadów."
	@echo "  make sync-status   - Wyświetla czas od ostatniej synchronizacji dla każdej grupy."

# Wszystkie boty naraz
# scrape:
# 	@echo "Uruchamianie scrapowania dla wszystkich botów..."
# 	uv run python -m src.scripts.scrape_posts --bot all

# classify:
# 	@echo "Uruchamianie klasyfikacji dla wszystkich botów..."
# 	uv run python -m src.scripts.classify_posts --bot all

# send-messages:
# 	@echo "Uruchamianie wysyłania wiadomości dla wszystkich botów..."
# 	uv run python -m src.scripts.send_messages --bot all

# Bot leasing
scrape:
	@echo "Uruchamianie scrapowania dla bota: leasing..."
	uv run python -m src.scripts.scrape_posts --bot leasing

classify:
	@echo "Uruchamianie klasyfikacji dla bota: leasing..."
	uv run python -m src.scripts.classify_posts --bot leasing

send:
	@echo "Uruchamianie wysyłania wiadomości dla bota: leasing..."
	uv run python -m src.scripts.send_messages --bot leasing

# Bot car_buyers
scrape-car-buyers:
	@echo "Uruchamianie scrapowania dla bota: car_buyers..."
	uv run python -m src.scripts.scrape_posts --bot car_buyers

classify-car-buyers:
	@echo "Uruchamianie klasyfikacji dla bota: car_buyers..."
	uv run python -m src.scripts.classify_posts --bot car_buyers

send-car-buyers:
	@echo "Uruchamianie wysyłania wiadomości dla bota: car_buyers..."
	uv run python -m src.scripts.send_messages --bot car_buyers

# Narzędzia
list:
	@echo "Uruchamianie skryptu do listowania wiadomości..."
	uv run python -m src.scripts.list_posts

sync-status:
	@echo "Sprawdzanie czasu od ostatniej synchronizacji grup..."
	uv run python -m src.scripts.check_sync_status

admin:
	@echo "Uruchamianie panelu admina..."
	uv run uvicorn src.admin_panel.app:app --reload

setup:
	@echo "Instalowanie zależności..."
	uv sync

.PHONY: help scrape classify send-messages scrape-leasing classify-leasing send-leasing scrape-car-buyers classify-car-buyers send-car-buyers list sync-status admin setup
