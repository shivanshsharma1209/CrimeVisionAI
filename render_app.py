import os
import sys

# रेंडर पर 512MB RAM का क्रैश (OOM) रोकने के लिए भारी AI मॉडल्स को पूरी तरह से मॉक (Mock) करना
class MockModule:
    def __getattr__(self, name):
        return MockModule()
    def __call__(self, *args, **kwargs):
        return MockModule()

# भारी विज़न और ऑडियो प्रोसेसिंग इंजन को ब्लॉक करना ताकि वेट्स (.pt) डाउनलोड न हों
sys.modules['torch'] = MockModule()
sys.modules['torchvision'] = MockModule()
sys.modules['torchaudio'] = MockModule()
sys.modules['ultralytics'] = MockModule()
sys.modules['transformers'] = MockModule()
sys.modules['whisper'] = MockModule()

# अब बिना किसी रैम दबाव के आपके मुख्य FastAPI ऐप आर्किटेक्चर को लोड करना
try:
    from app import app
except ImportError:
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    from app import app

import uvicorn

if __name__ == "__main__":
    # Render द्वारा दिया गया पोर्ट उठाएं, नहीं तो डिफ़ॉल्ट 10000 यूज़ करें
    port = int(os.environ.get("PORT", 10000))
    # बिना रीलोड के सिंगल-थ्रेडेड लाइटवेट मोड में रन करें
    uvicorn.run("render_app:app", host="0.0.0.0", port=port, reload=False)
