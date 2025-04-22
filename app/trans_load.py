from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
import logging
from google.oauth2 import service_account
from google.cloud import bigquery
from pandas_gbq import to_gbq
import requests
import os
import json
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_spark_session():
    try:
        # Configuration GCP
        gcp_key_str = os.getenv("GCP_KEY")
        gcp_key = json.loads(gcp_key_str)

        # Initialisation de la session Spark
        spark = SparkSession.builder \
            .appName("RedditEmotionAnalysis") \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1") \
            .config("spark.executor.memory", "2g") \
            .config("spark.driver.memory", "1g") \
            .config("spark.driver.host", "trans_load") \
            .config("spark.sql.shuffle.partitions", "2") \
            .config("spark.network.timeout", "600s") \
            .config("spark.executor.heartbeatInterval", "300s") \
            .config("spark.ui.showConsoleProgress", "true") \
            .getOrCreate()

        logger.info("Initialisation de Spark terminée")
        return spark, gcp_key
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de Spark: {str(e)}")
        raise

def process_stream(spark, gcp_key):
    try:
        # Schéma des données Kafka
        schema = StructType([
            StructField("id", StringType()),
            StructField("text", StringType()),
            StructField("author", StringType()),
            StructField("subreddit", StringType()),
            StructField("timestamp", DoubleType())
        ])

        # Configuration Kafka
        kafka_options = {
            "kafka.bootstrap.servers": "kafka:9092",
            "subscribe": "reddit_comments",
            "startingOffsets": "earliest",
            "failOnDataLoss": "false"
        }

        # Lecture du stream Kafka
        df = spark.readStream \
            .format("kafka") \
            .options(**kafka_options) \
            .load()

        # Transformation des données
        processed_df = df.selectExpr("CAST(value AS STRING) AS json_value") \
            .select(from_json("json_value", schema).alias("data")) \
            .select("data.*")

        # Debug: Afficher le schéma
        logger.info("Schéma du DataFrame:")
        processed_df.printSchema()

        # Initialisation BigQuery
        bq_client = bigquery.Client.from_service_account_info(gcp_key)
        gbq_credentials = service_account.Credentials.from_service_account_info(gcp_key)

        # Fonction pour prédire les émotions
        def predict_emotion(text):
            try:
                response = requests.post(
                    "http://api:8000/predict/",
                    json={"text": text},
                    timeout=30
                )
                return response.json().get("emotion_predict", "unknown")
            except Exception as e:
                logger.error(f"Erreur lors de la prédiction d'émotion: {str(e)}")
                return "error"

        # Fonction pour écrire dans BigQuery
        def write_to_bigquery(batch_df, batch_id):
            try:
                if batch_df.count() == 0:
                    logger.info(f"Batch {batch_id} vide - ignoré")
                    return

                logger.info(f"Traitement du batch {batch_id} avec {batch_df.count()} lignes")

                pandas_df = batch_df.toPandas()
                pandas_df["emotion"] = pandas_df["text"].apply(predict_emotion)

                # Écriture dans BigQuery
                table_id = "streamotion-456918.Database.reddit_emotions"
                to_gbq(
                    pandas_df,
                    destination_table=table_id,
                    project_id=gcp_key['project_id'],
                    if_exists="append",
                    credentials=gbq_credentials
                )

                logger.info(f"Batch {batch_id} écrit dans BigQuery ({len(pandas_df)} lignes)")
            except Exception as e:
                logger.error(f"Erreur critique dans le batch {batch_id}: {str(e)}")

        # Démarrage du streaming
        query = processed_df.writeStream \
            .outputMode("append") \
            .foreachBatch(write_to_bigquery) \
            .option("checkpointLocation", "/tmp/checkpoints") \
            .start()

        logger.info("Démarrage du streaming...")
        return query

    except Exception as e:
        logger.error(f"Erreur lors du traitement du stream: {str(e)}")
        raise

def main():
    spark, gcp_key = None, None
    try:
        spark, gcp_key = create_spark_session()
        query = process_stream(spark, gcp_key)
        query.awaitTermination()
    except KeyboardInterrupt:
        logger.info("Arrêt demandé...")
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
    finally:
        if spark:
            spark.stop()
            logger.info("Session Spark fermée")

if __name__ == "__main__":
    main()
