from google.cloud import bigquery
from google.oauth2 import service_account
import plotly.express as px
import plotly.graph_objects as go
from scipy.spatial.distance import cdist
from math import pi, sin, cos
from ipywidgets import interact, FloatSlider
import numpy as np
import streamlit as st

class Graph():

    def __init__(self):
        creds_dict = st.secrets["gcp_credentials"]
        self.credentials = service_account.Credentials.from_service_account_info(creds_dict)
        self.project_id = creds_dict["project_id"]
        self.client = bigquery.Client(
            credentials=self.credentials,
            project=self.project_id
        )

    def graph_emotion(self):
        query = """
        SELECT emotion, COUNT(*) as count
        FROM streamotion-456918.Database.reddit_emotions
        GROUP BY emotion
        """
        df = self.client.query(query).to_dataframe()
        df = df[df['emotion'] != "PREDICTION_ERROR"]
        df['proportion'] = df['count'] / df['count'].sum() * 100

        fig = px.scatter(
            df,
            x=np.cos(np.linspace(0, 2*np.pi, len(df), endpoint=False)),
            y=np.sin(np.linspace(0, 2*np.pi, len(df), endpoint=False)),
            size='proportion',
            color='emotion',
            text='emotion',
            size_max=100,
            color_discrete_sequence=px.colors.qualitative.Pastel,
            title="Mapping des emotions"
        )

        fig.update_traces(
            marker=dict(line=dict(width=2, color='DarkSlateGrey')),
            textfont=dict(size=14, color='white'),
            textposition='middle center'
        )

        fig.update_layout(
            plot_bgcolor='black',
            paper_bgcolor='black',
            xaxis=dict(showgrid=False, visible=False),
            yaxis=dict(showgrid=False, visible=False),
            showlegend=False,
            hovermode='closest',
            margin=dict(l=20, r=20, t=80, b=20),
            title_x=0.5,
            title_font=dict(size=20)
        )

        for r in [0.5, 1, 1.5]:
            fig.add_shape(
                type="circle",
                xref="x", yref="y",
                x0=-r, y0=-r, x1=r, y1=r,
                line_color="lightgray",
                line_width=1,
                opacity=0.3
            )

        return fig

    def graph_comment(self):
        query = """
        SELECT *
        FROM streamotion-456918.Database.reddit_emotions
        """
        df = self.client.query(query).to_dataframe()
        random_index = np.random.randint(0, len(df))
        row_choice = df.iloc[random_index]
        return [row_choice['author'], row_choice['text'], row_choice['emotion']]
