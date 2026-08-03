import gradio as gr
from data_helpers import (
    PDF_DIR,
    get_contribution,
    list_communes,
    list_contributions,
    save_annotation,
)


def pdf_html(pdf_file: str | None) -> str:
    if not pdf_file:
        return "<em>PDF à intégrer.</em>"
    path = (PDF_DIR / pdf_file).resolve()
    if not path.exists():
        return f"<em>PDF introuvable : {pdf_file}</em>"
    src = f"/gradio_api/file={path}"
    return (
        f'<iframe src="{src}" width="100%" height="640px" '
        'style="border:1px solid #ddd;border-radius:8px;"></iframe>'
    )

def show(commune: str, idx: int):
    """Affiche la contribution n°idx de la commune."""
    contribs = list_contributions(commune)
    idx = max(0, min(idx, len(contribs) - 1))
    c = get_contribution(commune, idx)
    return (
        gr.update(choices=contribs, value=contribs[idx] if contribs else None),
        c["analyse"],
        c["header"],
        c["text"],
        pdf_html(c["pdf_file"]),
        c["is_anonymized"],
        c["is_of_interest"],
        idx,
    )

def render():
    """Construit l'onglet 'Par commune' et câble ses événements.

    Retourne (fonction, outputs) pour l'affichage initial : cet événement
    appartient au niveau Blocks, c'est app.py qui le branche (demo.load).
    """
    idx_state = gr.State(0)

    with gr.Row():
        with gr.Column(scale=1):
            commune = gr.Dropdown(
                list_communes(), value=list_communes()[0], label="Commune", filterable=True
            )
            contrib = gr.Dropdown(label="Contribution", filterable=True)
            analyse = gr.Markdown()
            with gr.Row():
                prev_btn = gr.Button("Précédente")
                next_btn = gr.Button("Suivante")

        with gr.Column(scale=2):
            header = gr.Markdown()
            text = gr.Textbox(label="Texte de la contribution", lines=18, interactive=False)
            anonymized = gr.Checkbox(label="Anonymisé")
            of_interest = gr.Checkbox(label="Contribution d'intérêt")
            save_btn = gr.Button("Enregistrer", variant="primary")
            status = gr.Markdown()

        with gr.Column(scale=2):
            gr.Markdown("#### PDF source")
            pdf = gr.HTML()

    outputs = [contrib, analyse, header, text, pdf, anonymized, of_interest, idx_state]

    commune.change(lambda c: show(c, 0), commune, outputs)
    contrib.input(
        lambda label, c: show(c, int(label.split("/")[0]) - 1 if "/" in label else 0),
        [contrib, commune],
        outputs,
    )
    prev_btn.click(lambda c, i: show(c, i - 1), [commune, idx_state], outputs)
    next_btn.click(lambda c, i: show(c, i + 1), [commune, idx_state], outputs)
    save_btn.click(save_annotation, [commune, idx_state, anonymized, of_interest], status)

    return lambda: show(list_communes()[0], 0), outputs
