from pathlib import Path
import gradio as gr
import plotly.offline
from data_helpers import PDF_DIR
from fastapi import Body
from fastapi.responses import FileResponse, HTMLResponse, Response
from views import commune, graph

STYLE = Path(__file__).parent / "views" / "style.css"


# VUE COMMUNES
with gr.Blocks(title="Cahiers de doléances") as demo:
    # barre de navigation : la vue graphe est une page à part (voir le docstring),
    # on y accède par un lien plutôt que par un onglet
    gr.HTML(
        '<div class="nav">'
        '<h1>Visualisation des contributions</h1>'
        '<a class="nav-lien" href="/graphe">Vue graphe des thèmes →</a>'
        "</div>"
    )

    with gr.Tab("Par commune"):
        load_fn, load_outputs = commune.render()

    demo.load(load_fn, None, load_outputs)


# VUE GRAPH DE TOPIC
app = gr.Server()
# no-store : recharger la page reprend les fichiers static/ à jour
_NO_STORE = {"Cache-Control": "no-store"}

@app.get("/graphe/api/config")
def graphe_config():
    return graph.config()


@app.post("/graphe/api/apercu")
def graphe_apercu(strate: str = Body(..., embed=True)):
    return graph.apercu(strate)


@app.post("/graphe/api/noeud")
def graphe_noeud(nom: str = Body(..., embed=True)):
    return graph.noeud(nom)


@app.get("/graphe/plotly.js")
def graphe_plotly_js():
    return Response(
        plotly.offline.get_plotlyjs(),
        media_type="text/javascript"
    )


@app.get("/graphe/app.js")
def graphe_app_js():
    return FileResponse(
        graph.STATIC / "app.js",
        media_type="text/javascript",
        headers=_NO_STORE
    )


@app.get("/graphe/style.css")
def graphe_style_css():
    return FileResponse(
        graph.STATIC / "style.css",
        media_type="text/css",
        headers=_NO_STORE
    )


@app.get("/graphe")
def graphe_index():
    return HTMLResponse(
        (graph.STATIC / "index.html").read_text(encoding="utf-8"),
        headers=_NO_STORE
    )


# le Blocks est monté en dernier : sa route "/" ne doit pas masquer /graphe
gr.mount_gradio_app(
    app,
    demo,
    path="/",
    allowed_paths=[str(PDF_DIR)],
    theme=gr.themes.Soft(),
    css_paths=[STYLE]
)


if __name__ == "__main__":
    app.launch()
