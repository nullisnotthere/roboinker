# Software for Speech-to-text, AI-powered 2-DOF Robotic Arm

The software that manages AI, speech-to-text, image processing, and motor control.

## How to Use

This software requires a Raspberry PI (5) and Arduino Uno configured with CNC shield
and DRV8825 stepper drivers.

However, the simulation code can be run on any machine given the correct
configurations and required installs.

Run:

```bash
git clone https://github.com/nullisnotthere/roboinker
cd roboinker/
pip install -r requirements.txt
python src/simulation/visualiser.py
```

## Configuration

`src/rpi/backend/image_generation/.env`

```env
# Dream AI sensitive environment variables
EMAIL='YOUR_DREAM_AI_EMAIL'
PASSWORD='YOUR_DREAM_AI_PASSWORD'
API_KEY='YOUR_DREAM_AI_API_KEY'
AUTHORIZATION_TOKEN='null'
```

`src/rpi/backend/prompt_processing/.env`

```env
# Deep AI sensitive environment variables
API_KEY='YOUR_DEEP_AI_API_KEY'
