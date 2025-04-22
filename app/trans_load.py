import os
import json
import logging
from dotenv import load_dotenv
import requests
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
from google.oauth2 import service_account
from google.cloud import bigquery
from pandas_gbq import to_gbq

# Chargement des variables d'environnement
load_dotenv()

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Clé GCP depuis .env (JSON string)
gcp_key = json.loads(os.getenv("GCP_KEY"))
credentials = service_account.Credentials.from_service_account_info(gcp_key)
bq_client = bigquery.Client(credentials=credentials, project=gcp_key['project_id'])

def get_spark_session():
    master_url = os.getenv('SPARK_MASTER_URL', 'spark://spark-master:7077')
    return SparkSession.builder \
        .appName("RedditEmotionAnalysis") \
        .config("spark.master", master_url) \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1") \
        .config("spark.executor.memory", "2g") \
        .config("spark.driver.memory", "1g") \
        .config("spark.driver.host", "trans_load") \
        .config("spark.sql.shuffle.partitions", "2") \
        .getOrCreate()

spark = get_spark_session()
logger.info("Spark session démarrée")

# Schéma Kafka
schema = StructType([
    StructField("id", StringType()),
    StructField("text", StringType()),
    StructField("author", StringType()),
    StructField("subreddit", StringType()),
    StructField("timestamp", DoubleType())
])

# Lecture du flux Kafka
df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "reddit_comments") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .load()

processed = df.selectExpr("CAST(value AS STRING) AS json") \
    .select(from_json("json", schema).alias("data")) \
    .select("data.*")

logger.info("Schéma du DataFrame traité :")
processed.printSchema()

# Prédiction et écriture
def predict_emotion(text):
    try:
        resp = requests.post(
            "http://api:8000/predict/", json={"text": text}, timeout=10)
        return resp.json().get("emotion_predict", "unknown")
    except Exception as e:
        logger.error(f"Erreur prédiction: {e}")
        return "error"

def write_batch(df_batch, batch_id):
    logger.info(f"Ecriture du batch {batch_id}...")
    pdf = df_batch.toPandas()
    pdf['emotion'] = pdf['text'].apply(predict_emotion)

    to_gbq(
        pdf,
        destination_table="streamotion-456918.Database.reddit_emotions",
        project_id=gcp_key['project_id'],
        if_exists="append",
        credentials=credentials
    )
    logger.info(f"Batch {batch_id} inséré ({len(pdf)} lignes)")

query = processed.writeStream \
    .outputMode("append") \
    .foreachBatch(write_batch) \
    .option("checkpointLocation", "/tmp/checkpoints") \
    .start()

logger.info("Streaming démarré")

try:
    query.awaitTermination()
except KeyboardInterrupt:
    logger.info("Arrêt manuel")
    query.stop()
finally:
    spark.stop()
    logger.info("Spark fermé")
