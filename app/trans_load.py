from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, udf
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
import logging
from transformers import pipeline
from google.oauth2 import service_account
from google.cloud import bigquery
from pandas_gbq import to_gbq
import requests
import os
import json
from dotenv import load_dotenv


load_dotenv()


gcp_key_str = os.getenv("GCP_KEY")
gcp_key = json.loads(gcp_key_str)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

schema = StructType([
    StructField("id", StringType()),
    StructField("text", StringType()),
    StructField("author", StringType()),
    StructField("subreddit", StringType()),
    StructField("timestamp", DoubleType())
])

spark = SparkSession.builder \
    .appName("Reddit Streaming") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0") \
    .config("spark.executor.memory", "4g") \
    .config("spark.driver.memory", "4g") \
    .getOrCreate()

logger.info("Démarrage de l'application Spark...")

kafka_options = {
    "kafka.bootstrap.servers": "kafka:9092",
    "subscribe": "reddit_comments",
    "startingOffsets": "earliest"
}

df = spark.readStream \
    .format("kafka") \
    .options(**kafka_options) \
    .load() \
    .selectExpr("CAST(value AS STRING) AS json_value")

processed_df = df.select(from_json("json_value", schema).alias("data")) \
    .select("data.*") \

bq_client = bigquery.Client.from_service_account_info(gcp_key)
gbq_credentials = service_account.Credentials.from_service_account_info(gcp_key)

def predict_emotion(text):
    response = requests.post("http://127.0.0.1:8000/predict/", json={"text": text})
    return response.json().get("emotion_predict", "unknown")

def write_to_bigquery(batch_df, batch_id):
    try:
        pandas_df = batch_df.toPandas()
        pandas_df["emotion"] = pandas_df["text"].apply(lambda x: predict_emotion(x))
        table_id = "streamotion-456918.Database.reddit_emotions"
        to_gbq(pandas_df, destination_table=table_id, project_id=gcp_key['project_id'], if_exists='append', credentials=gbq_credentials)
        logger.info(f"Batch {batch_id} envoyé avec succès vers BigQuery.")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi vers BigQuery: {str(e)}")

query = processed_df.writeStream \
    .outputMode("append") \
    .foreachBatch(write_to_bigquery) \
    .start()

query.awaitTermination()
