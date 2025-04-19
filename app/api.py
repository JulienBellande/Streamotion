from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline
from deep_translator import GoogleTranslator


class Agent():
    def __init__(self):
        self.translator = GoogleTranslator(source='auto', target='en')
        self.classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", top_k=1)

    def predict(self, text):
        translated = self.translator.translate(text)
        result = self.classifier(translated)
        return result[0][0]["label"]

app = FastAPI()
agent = Agent()

class TextInput(BaseModel):
    text: str

@app.post("/predict/")
def predict_sentiment(payload: TextInput):
    result = agent.predict(payload.text)
    return {"emotion_predict": result}
