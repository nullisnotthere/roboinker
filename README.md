
<div align="center">

```py

"██████╗  ██████╗ ██████╗  ██████╗ " ██╗███╗   ██╗██╗  ██╗███████╗██████#╗
" ██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗" ██║████╗  ██║██║ ██╔╝██╔════╝██╔══██#╗
" ██████╔╝██║   ██║██████╔╝██║   ██║" ██║██╔██╗ ██║█████╔╝ █████╗  ██████#╔╝
" ██╔══██╗██║   ██║██╔══██╗██║   ██║" ██║██║╚██╗██║██╔═██╗ ██╔══╝  ██╔══██#╗
" ██║  ██║╚██████╔╝██████╔╝╚██████╔╝" ██║██║ ╚████║██║  ██╗███████╗██║  ██#║
" ╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ "#╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝   ╚═╝

```

</div>

# Software for Speech-to-text, AI-powered 2-DOF Robotic Arm

Provides all of the software for a 3D-printed, 2-DOF robotic arm that draws images
with a pen using AI and speech recognition. The repo provides a
[visualiser](https://github.com/nullisnotthere/roboinker/blob/main/src/simulation/visualiser.py)
script to demonstrate the backend processes in action.

This is for my Year 12 Systems Engineering final project.

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

## Code Flow

1. Transcribe speech from microphone with
   [Vosk API](https://github.com/alphacep/vosk-api/tree/master/python)
2. Extract key ideas from voice prompt using a [Deep AI](https://deepai.org/)
   [API wrapper](https://github.com/nullisnotthere/roboinker/tree/main/src/rpi/backend/prompt_processing/deep_ai_wrapper)
3. Tune the prompt for image generation and pass it to a [Dream AI](https://dream.ai/)
   [API wrapper](https://github.com/nullisnotthere/roboinker/blob/main/src/rpi/backend/image_generation/dream_api_wrapper.py)
4. Convert the generated image to drawable contours using
   [various algorithms](https://github.com/nullisnotthere/roboinker/blob/main/src/rpi/backend/image_processing/image_processing.py)
5. Using the contour points, calculate and store the robotic arm's motor angles
   and drawing instructions in the
   [`output.angles`](https://github.com/nullisnotthere/roboinker/tree/main/data)
   file
6. Visualise the robotic arm's drawing process using
   [inverse kinematics](https://github.com/nullisnotthere/roboinker/tree/main/src/rpi/backend/ik)
