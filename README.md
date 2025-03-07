# Software for Speech-to-text, AI-powered 2-DOF Robotic Arm

This is all of the software that manages AI, speech-to-text, image processing,
and motor control.

## How to Use

This software requires a **Raspberry PI (5)** and **Arduino Uno** configured with
**CNC shield**
and **DRV8825 stepper drivers**.
However, the simulation code can be run on any machine given the correct
configurations and required installs.

### Run the simulation code

```bash
git clone https://github.com/nullisnotthere/roboinker
cd roboinker/
pip install -r requirements.txt
python src/simulation/visualiser.py
```

## Configuration

This software depends on two (free) external AI web apps;
[Deep AI](https://deepai.org/) and [Dream AI](https://dream.ai/create).
An account will need to be created for each of these websites to
gain access to the required API keys and Authorization Tokens.

`.env`

```env
# Sensitive environment variables for Dream AI
DREAM_AI_EMAIL='Your Dream AI email'
DREAM_AI_PASSWORD='Your Dream AI password'
DREAM_AI_API_KEY='Your Dream AI API key'

# Do not configure. This will automatically be retrieved.
DREAM_AI_AUTH_TOKEN='null'


# Sensitive environment variables for Deep AI
DEEP_AI_API_KEY='Your Deep AI API key'
```

### How to get Dream AI API Key

1. [Sign Up to Dream AI](https://dream.ai/profile)
2. Ctrl+Shift+I and navigate to `Storage` tab
3. Navigate to `IndexedDB`/`https://dream.ai`/`firebaseLocalStorageDb (default)`/`firebaseLocalStorage`
4. Click the `firebase:authUser` entry
5. On the right navigate to `value`/`apiKey` and (right-click) copy the value
6. Use this as the `DREAM_AI_API_KEY` value in `.env`

### How to get Deep AI API Key

1. [Sign up to Deep AI](https://deepai.org/)
2. Navigate to [your dashboard](https://deepai.org/dashboard/profile)
3. Copy your API key
