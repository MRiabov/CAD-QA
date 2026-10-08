"""Training and evaluation stack for CAD-QA.

This package owns every training and evaluation surface: the answer grader
(``grading/``), the Harbor runner/grader (``harbor.py``), experiment
orchestration (``experiment.py``), and the cross-package ``cadqa`` CLI
(``cli.py``). It consumes ``dataset/`` outputs through the rows I/O contract
only; ``dataset/`` never imports this package.
"""
