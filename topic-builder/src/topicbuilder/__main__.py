import typer

from topicbuilder.app import display
from topicbuilder.tasks.discover_parents import discover_parents
from topicbuilder.tasks.discover_topics import discover_topics
from topicbuilder.tasks.factorize import factorize
from topicbuilder.tasks.label import label
from topicbuilder.tasks.screen import screen

app = typer.Typer(no_args_is_help=True, help="Topic modeling CLI with independent tasks.")
app.command("discover-topics")(discover_topics)
app.command("discover-parents")(discover_parents)
app.command()(display)
app.command()(factorize)
app.command()(label)
app.command()(screen)


if __name__ == "__main__":
    app()
