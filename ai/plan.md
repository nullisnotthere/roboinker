# Flow

- _refresh_tokens()
  - Calls:
    - _get_auth_token()
      - Solved via request username and password login
      - _get_validation_token(manual_login=False)
      - Solved via headless browser JavaScript script
      - headless browser login saved in cookies
    - Stores said tokens in .env
- _load_headers()
  - returns headers defined in .env and headers.json
- generate_image()
  - Tries to connect to dream.ai with headers provided by _load_headers()
  - If error=token expired then call _refresh_tokens()
