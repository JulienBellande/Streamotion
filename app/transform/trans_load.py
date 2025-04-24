from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
import logging, os, json, requests
from google.oauth2 import service_account
from google.cloud import bigquery
from pandas_gbq import to_gbq
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

gcp_key = json.loads(os.getenv("GCP_KEY"))
bq_client = bigquery.Client.from_service_account_info(gcp_key)
gbq_credentials = service_account.Credentials.from_service_account_info(gcp_key)

# Schéma Kafka
schema = StructType([
    StructField("id", StringType()),
    StructField("text", StringType()),
    StructField("author", StringType()),
    StructField("subreddit", StringType()),
    StructField("timestamp", DoubleType())
])

# SparkSession sans master() pour prendre le master du spark-submit
spark = SparkSession.builder \
    .appName("RedditEmotionAnalysis") \
    .getOrCreate()

logger.info("Spark ready")

# Options Kafka
kafka_options = {
    "kafka.bootstrap.servers": "kafka:9092",
    "subscribe": "reddit_comments",
    "startingOffsets": "earliest",
    "failOnDataLoss": "false"
}

# Lecture du stream
kafka_df = spark.readStream \
    .format("kafka") \
    .options(**kafka_options) \
    .load()

# 1) DEBUG : affichez les messages bruts dans les logs
raw_df = kafka_df.selectExpr("CAST(value AS STRING) AS raw")
debug_query = raw_df.writeStream \
    .format("console") \
    .outputMode("append") \
    .option("truncate", "false") \
    .start()

# 2) transformation JSON → colonnes
processed_df = raw_df \
    .select(from_json("raw", schema).alias("data")) \
    .select("data.*")

# Fonctions auxiliaires
def predict_emotion(text):
    try:
        resp = requests.post("http://api:8000/predict/", json={"text": text}, timeout=10)
        return resp.json().get("emotion_predict", "unknown")
    except Exception as e:
        logger.error(f"Erreur prédiction: {e}")
        return "error"

def write_to_bigquery(batch_df, batch_id):
    logger.info(f"Batch {batch_id}")
    pdf = batch_df.toPandas()
    pdf["emotion"] = pdf["text"].apply(predict_emotion)
    to_gbq(pdf,
           destination_table="streamotion-456918.Database.reddit_emotions",
           project_id=gcp_key["project_id"],
           if_exists="append",
           credentials=gbq_credentials)
    logger.info(f"Batch {batch_id} writen ({len(pdf)} rows)")

# 3) vraie écriture
query = processed_df.writeStream \
    .outputMode("append") \
    .foreachBatch(write_to_bigquery) \
    .option("checkpointLocation", "/tmp/checkpoints") \
    .start()

logger.info("Streaming started")
query.awaitTermination()
