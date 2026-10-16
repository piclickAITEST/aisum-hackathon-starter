"""How much of the team's LLM budget is left.  Run:  .venv/bin/python -m src.budget

Two read-only lookups on the LLM gateway, with the app's LLM key from .env:
  /key/info                  → which team this key belongs to
  /team/info?team_id=…       → the team's budget and what it has spent
The budget is shared by both of the team's LLM keys (app and Claude Code), so the
spend shown is the two together. Spend reaches the gateway a little after each call.
"""
import httpx

from .config import MODEL, OPENAI_API_KEY, OPENAI_BASE_URL

GATEWAY = OPENAI_BASE_URL.rstrip("/").removesuffix("/v1")


def main() -> None:
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    with httpx.Client(base_url=GATEWAY, headers=headers, timeout=30) as gw:
        key = gw.get("/key/info")
        if key.is_error:
            raise SystemExit(f"LLM gateway answered HTTP {key.status_code} — check "
                             f"OPENAI_API_KEY in .env (the LLM key for your app).")
        team_id = key.json()["info"].get("team_id")
        team = gw.get("/team/info", params={"team_id": team_id}).json()["team_info"]
        models = [m["id"] for m in gw.get("/v1/models").json()["data"]]

    budget, spent = team.get("max_budget"), team.get("spend") or 0.0
    print(f"Team       {team.get('team_alias') or team_id}")
    if budget is None:
        print(f"Spent      ${spent:.2f}   (no budget set for this team)")
    else:
        print(f"Budget     ${budget:.2f}")
        print(f"Spent      ${spent:.2f}   (app key + Claude Code key together)")
        print(f"Remaining  ${budget - spent:.2f}")
    print(f"\nModels this key can use: {', '.join(models)}")
    print(f"MODEL in .env: {MODEL}" + ("" if MODEL in models else "   <- not in the list above"))


if __name__ == "__main__":
    main()
