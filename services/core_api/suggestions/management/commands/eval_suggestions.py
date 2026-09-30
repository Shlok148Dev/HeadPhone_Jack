"""Offline evaluation of friend suggestions (Tech Bible 5.6); logs a run to artifacts/ml."""

import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Evaluate friend suggestions: Recall@20, coverage, safety."

    def handle(self, *args, **options):
        from jingle_ml.evaluate import evaluate
        from jingle_ml.tasks import load_graph, load_taste
        from jingle_ml.tracking import log_run

        g = load_graph()
        vecs, tops = load_taste()
        metrics = evaluate(g, vecs, tops)
        log_run("suggestions-eval", params={"users": len(g.people)}, metrics=metrics)
        self.stdout.write(json.dumps(metrics))
