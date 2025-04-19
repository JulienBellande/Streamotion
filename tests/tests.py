from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)

def test_predict_endpoint():
    response = client.post("/predict/", json={"text": "Je suis très heureux aujourd'hui !"})
    assert response.status_code == 200
    result = response.json()
    assert "emotion_predict" in result
    assert result["emotion_predict"] in ["joy", "anger", "sadness", "fear", "love", "surprise"]
