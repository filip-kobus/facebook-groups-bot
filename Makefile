# Domyślne zadanie, wyświetla pomoc
help:
	@echo "Dostępne komendy:"
	@echo "  make scrape        - Uruchamia proces scrapowania i zapisywania leadów do bazy danych."
	@echo "  make sync-status   - Wyświetla czas od ostatniej synchronizacji dla każdej grupy."
	@echo "  make send-messages - Wysyła wiadomości do leadów z ostatniego dnia."
	@echo "  make list-messages - Wyświetla listę wiadomości wysłanych w ostatnim dniu."
	@echo "  make setup         - Instaluje zależności projektu."

scrape:
	@echo "Uruchamianie skryptu scrapującego..."
	uv run python -m src.scripts.scrape_posts

send-messages:
	@echo "Uruchamianie skryptu do wysyłania wiadomości..."
	uv run python -m src.scripts.send_messages

list:
	@echo "Uruchamianie skryptu do listowania wiadomości..."
	uv run python -m src.scripts.list_posts

setup:
	@echo "Instalowanie zależności..."
	uv sync

.PHONY: help scrape send-messages list-messages setup classify sync-status

classify:
	@echo "Uruchamianie skryptu do klasyfikacji postów..."
	uv run python -m src.scripts.classify_posts

sync-status:
	@echo "Sprawdzanie czasu od ostatniej synchronizacji grup..."
	uv run python -m src.scripts.check_sync_status

admin:
	@echo "Uruchamianie panelu admina..."
	uv run uvicorn src.admin_panel.app:app --reload
