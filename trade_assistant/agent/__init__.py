"""Brick 5: the agent that prepares your monthly plan.

    facts.py     every figure from bricks 1-4, numbered F1, F2... (the only sources of the models)
    roles.py     analyst, devil's advocate, portfolio manager: prompts and strict answer formats
    checks.py    invented figures flagged; a plan breaking your rules is rejected
    pipeline.py  runs the three roles, falls back to the calculated plan when the AI fails, stores
                 the plan as a draft waiting for your decision
"""
