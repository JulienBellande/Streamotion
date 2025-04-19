import streamlit as st
from graph import Graph
import time
import os

graph = Graph()

st.set_page_config(page_title="Streamotion", layout="wide")
st.title("Streamotion")
st.markdown("Voir le code sur GitHub : https://github.com/JulienBellande/streamotion")

page = st.selectbox("Page:", ["Streamotion", "Streamotion: Documentation"])

if page == "Streamotion":
    col1, col2 = st.columns([8, 3])

    with col1:
        if st.button("🔁 Rafraîchir le graphique"):
            st.rerun()

        st.plotly_chart(graph.graph_emotion(), use_container_width=True)

        st.info("""
        💡 **Info :**
        La taille des sphères reflète la proportion de chaque émotion.
        Passez votre souris dessus pour voir les détails précis.
        Pour une expérience encore plus dynamique, connectez-vous lors d’une **grande annonce politique** — vous verrez les sphères bouger rapidement ! 😉
        """)

        st.warning("""
        ⚠️ **Attention :**
        Les commentaires affichés sont extraits en direct et aléatoirement.
        Aucun système de modération n’a encore été implémenté.
        Certains propos peuvent donc être inappropriés ou offensants.
        """)

    with col2:
        st.subheader("Commentaires analysés")
        comment_placeholder = st.empty()

        while True:
            comment = graph.graph_comment()

            with comment_placeholder.container():
                st.markdown(f"👤 **Auteur :** {comment[0]}")
                st.markdown(f"💬 **Commentaire :** {comment[1]}")
                st.markdown(f"🎭 **Émotion détectée :** `{comment[2]}`")
                st.markdown("—" * 20)

            time.sleep(5)

elif page == "📄 Documentation":
    st.markdown("## 📚 Documentation")

    readme_path = os.path.join(os.getcwd(), "docs", "README.md")

    with open(readme_path, "r") as file:
        content = file.read()
        st.markdown(content)
