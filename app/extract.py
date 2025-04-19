import praw
from kafka import KafkaProducer
import json
import time
import logging
import os
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

reddit = praw.Reddit(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    user_agent=os.getenv("USER_AGENT")
)
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    api_version=(2, 5, 0)
)
subreddit = reddit.subreddit("AskFrance")

try:
    logger.info("Démarrage de la collecte des commentaires Reddit...")
    for comment in subreddit.stream.comments(skip_existing=True):
        try:
            message = {
                "id": comment.id,
                "text": comment.body,
                "author": str(comment.author),
                "subreddit": str(comment.subreddit),
                "timestamp": time.time()
            }

            producer.send("reddit_comments", message)
            logger.info(f"Message envoyé: {comment.id}")

            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Erreur lors du traitement du commentaire: {e}")
            time.sleep(5)
except KeyboardInterrupt:
    logger.info("Arrêt du producteur")
finally:
    producer.close()
    logger.info("Producteur Kafka fermé")
