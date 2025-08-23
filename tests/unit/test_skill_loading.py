import ws_server.routing.skills as skills_mod
from ws_server.routing.skills import BaseSkill


def test_load_all_skills_returns_instances():
    skills = skills_mod.load_all_skills()
    assert skills, "Es sollten Skills geladen werden"
    assert all(isinstance(skill, BaseSkill) for skill in skills)
