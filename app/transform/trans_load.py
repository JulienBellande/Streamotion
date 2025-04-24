import os
import sys
import json
import logging
import traceback
import requests
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
from google.oauth2 import service_account
from pandas_gbq import to_gbq


load_dotenv()

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("trans_load")

# 2) Clé GCP
try:
    gcp_key = json.loads(os.environ["GCP_KEY"])
    creds = service_account.Credentials.from_service_account_info(gcp_key)
    project_id = gcp_key["project_id"]
    logger.info("Clé GCP chargée avec succès")
except Exception:
    logger.error("Impossible de charger la variable GCP_KEY depuis .env")
    traceback.print_exc(file=sys.stdout)
    sys.exit(1)

# 3) Schéma Kafka
schema = StructType([
    StructField("id", StringType()),
    StructField("text", StringType()),
    StructField("author", StringType()),
    StructField("subreddit", StringType()),
    StructField("timestamp", DoubleType())
])

# 4) Prédiction avec l’API FastAPI
def predict_emotion(text: str) -> str:
    try:
        resp = requests.post(
            "http://api:8000/predict/",
            json={"text": text},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json().get("emotion_predict", "unknown")
    except Exception as e:
        logger.error(f"Erreur prédiction («{text[:30]}…»): {e}")
        return "error"

# 5) Callback d’écriture dans BigQuery
def write_to_bigquery(batch_df, batch_id):
    try:
        logger.info(f"[Batch {batch_id}] début")
        if batch_df.rdd.isEmpty():
            logger.info(f"[Batch {batch_id}] vide, skip")
            return
        pdf = batch_df.toPandas()
        pdf["emotion"] = pdf["text"].apply(predict_emotion)
        to_gbq(
            dataframe=pdf,
            destination_table=f"{project_id}.Database.reddit_emotions",
            project_id=project_id,
            if_exists="append",
            credentials=creds
        )
        logger.info(f"[Batch {batch_id}] écrit {len(pdf)} lignes")
    except Exception:
        logger.exception(f"[Batch {batch_id}] exception")

# 6) Main Spark Streaming
def main():
    try:
        spark = SparkSession.builder \
            .appName("RedditEmotionAnalysis") \
            .getOrCreate()
        logger.info("Spark session démarrée")

        # Hard-coded Kafka parameters
        kafka_df = (
            spark.readStream
                 .format("kafka")
                 .option("kafka.bootstrap.servers", "kafka:9092")
                 .option("subscribe", "reddit_comments")
                 .option("startingOffsets", "earliest")
                 .option("failOnDataLoss", "false")
                 .load()
        )

        processed = (
            kafka_df
            .selectExpr("CAST(value AS STRING) AS raw")
            .select(from_json("raw", schema).alias("data"))
            .select("data.*")
        )

        query = (
            processed.writeStream
                     .outputMode("append")
                     .foreachBatch(write_to_bigquery)
                     .option("checkpointLocation", "/tmp/checkpoints")
                     .start()
        )

        logger.info("Streaming démarré")
        query.awaitTermination()

    except Exception:
        logger.exception("Erreur fatale du driver Spark")
        sys.exit(1)

if __name__ == "__main__":
    main()
